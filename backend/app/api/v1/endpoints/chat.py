
from __future__ import annotations

import re
from time import perf_counter

import json

from fastapi.responses import JSONResponse, StreamingResponse

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from langsmith import traceable
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import error_response
from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.chat import ChatMessageCreate, ChatSessionCreate
from app.services.auth import get_current_user
from app.services.ai.action_agent import execute_action
from app.services.ai.audit_logger import log_ai_interaction
from app.services.ai.policy_rag_service import (
    answer_policy_question,
    stream_policy_answer,
)
from app.services.ai.router import classify_message
from app.services.ai.sql_service import answer_sql_question

from app.services.ai.orchestration_graph import run_hrms_graph
from app.services.ai.hitl_service import (
    cancel_confirmation,
    claim_confirmation,
    finish_confirmation,
)



router = APIRouter()


# Screen destructive SQL requests before semantic intent classification.
# This is a routing safeguard; sql_guardrails remains the authoritative SQL validator.
_UNSAFE_SQL_KEYWORDS = re.compile(
    r"\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|PRAGMA|ATTACH|DETACH)\b",
    re.IGNORECASE,
)
_EXPLICIT_SQL_EXECUTION = re.compile(
    r"\b(?:run|execute)\s+(?:(?:this|the)\s+)?(?:sql|query)\b",
    re.IGNORECASE,
)
_SQL_LABELLED_DESTRUCTIVE_STATEMENT = re.compile(
    r"\b(?:sql|query)\s*[:=]\s*(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|PRAGMA|ATTACH|DETACH)\b",
    re.IGNORECASE,
)
_DIRECT_DESTRUCTIVE_STATEMENT = re.compile(
    r"^\s*(?:"
    r"INSERT\s+INTO\b|"
    r"UPDATE\s+[A-Za-z_][\w.]*\s+SET\b|"
    r"DELETE\s+FROM\b|"
    r"DROP\s+(?:TABLE|DATABASE|INDEX|VIEW|SCHEMA)\b|"
    r"ALTER\s+(?:TABLE|DATABASE|INDEX|VIEW|SCHEMA)\b|"
    r"CREATE\s+(?:TABLE|DATABASE|INDEX|VIEW|SCHEMA|TRIGGER|PROCEDURE|FUNCTION)\b|"
    r"REPLACE\s+INTO\b|"
    r"TRUNCATE(?:\s+TABLE)?\b|"
    r"PRAGMA\b|ATTACH\b|DETACH\b"
    r")",
    re.IGNORECASE,
)
_EXPLANATION_REQUEST = re.compile(
    r"\b(?:explain|describe|define|what does|what is|meaning of|tell me about)\b",
    re.IGNORECASE,
)
_NATURAL_LANGUAGE_DESTRUCTIVE_REQUEST = re.compile(
    r"\b(?:delete|remove|erase|wipe|purge|drop|truncate)\b"
    r"(?:(?!\b(?:explain|describe|define)\b).){0,150}"
    r"\b(?:all\s+)?"
    r"(?:employee|employees|staff|users|customers|records|record|"
    r"data|rows|row|database|table|tables)\b"
    r"|"
    r"\b(?:delete|remove|erase|wipe|purge|drop|truncate)\b"
    r".{0,100}"
    r"\b(?:from|in)\s+(?:the\s+)?"
    r"(?:HRMS\s+)?(?:database|table|system)\b",
    re.IGNORECASE,
)

# Questions about whether a half-day leave is permitted are policy questions,
# not requests to execute a leave action. Keep explicit action requests on the
# existing action-agent path.
_HALF_DAY_LEAVE_POLICY_QUESTION = re.compile(
    r"\b(?:half[ -]day|half day)\b.*\bleave\b|"
    r"\bleave\b.*\b(?:half[ -]day|half day)\b",
    re.IGNORECASE,
)
_EXPLICIT_LEAVE_ACTION = re.compile(
    r"\b(?:submit|apply for|request|create|cancel|withdraw|approve|reject)\b",
    re.IGNORECASE,
)


def classify_copilot_intent(message: str) -> str:
    """Route policy questions to RAG without hijacking explicit HR actions."""
    question = (message or "").strip()

    if not question:
        return "unknown"

    # Explicit project assignment requests are HR actions, even when the
    # project name contains policy-related words (for example, "HR Policy Copilot").
    # Route these before SQL and policy keyword detection so authorization is
    # enforced by the Action Agent.
    project_assignment_request = bool(
        re.search(
            r"\b(?:assign|reassign|allocate)\b.{0,180}\b(?:employee|staff member)\b"
            r".{0,180}\b(?:to|onto)\b"
            r"|\b(?:assign|reassign|allocate)\b.{0,180}\bproject\b"
            r".{0,180}\b(?:employee|staff member)\b",
            question,
            re.IGNORECASE | re.DOTALL,
        )
    )
    if project_assignment_request:
        return "action"

    # Explicit database/SQL lookup requests must be routed before policy-keyword
    # detection. A policy-related word can be part of a project or other record
    # name (for example, "HR Policy Copilot project") and must not hijack a
    # read-only employee/project lookup into Policy RAG.
    explicit_sql_lookup = bool(
        re.search(
            r"\b(?:read[ -]only\s+(?:sql\s+)?query|sql\s+query|database\s+query|"
            r"query\s+against\s+(?:the\s+)?(?:existing\s+)?(?:hrms\s+)?database)\b",
            question,
            re.IGNORECASE,
        )
        or (
            re.search(r"\b(?:who|which|show|list|find|get|return)\b", question, re.IGNORECASE)
            and re.search(
                r"\b(?:assigned\s+to|project\s+assignments?|employees?\s+(?:know|with)|"
                r"employee\s+skills?|department\s+counts?|ongoing\s+projects?)\b",
                question,
                re.IGNORECASE,
            )
        )
    )
    if explicit_sql_lookup:
        return "sql"

    # Explicit ticket assignment/reassignment is an HR action, even when the
    # request also mentions eligible employees, HR/payroll, or asks for a
    # suitable assignee. Detect it BEFORE broad policy keywords such as
    # "eligible" so it cannot be hijacked by Policy RAG.
    ticket_assignment_request = bool(
        re.search(
            r"\b(?:assign|reassign)\b.{0,120}\b(?:ticket|it)\b"
            r"|\b(?:find|locate|show|get|check)\b.{0,140}"
            r"\b(?:support\s+)?ticket\s*(?:#|id\s*)?\d+\b"
            r".{0,220}\b(?:assign|reassign)\b",
            question,
            re.IGNORECASE | re.DOTALL,
        )
    )
    if ticket_assignment_request:
        return "action"

    # Questions asking about policy, eligibility, entitlements,
    # procedures, restrictions, or approval requirements belong to Policy RAG.
    # Keep this broad policy check AFTER explicit operational actions.
    policy_question = bool(
        re.search(
            r"\b(policy|policies|eligibility|eligible|entitlement|"
            r"entitlements|restrictions|approval process|"
            r"how to apply|application process|leave allowance|"
            r"days per year|leave balance policy)\b",
            question,
            re.IGNORECASE,
        )
        or (
            re.search(r"\b(what|which|how|when|who|explain|describe)\b", question, re.IGNORECASE)
            and re.search(r"\b(annual leave|casual leave|sick leave|earned leave|remote work)\b", question, re.IGNORECASE)
        )
    )

    # Explanatory policy questions must not become action requests merely
    # because they contain phrases such as "how to apply for leave".
    if policy_question:
        return "policy"

    # Preserve the existing half-day leave policy safeguard.
    if (
        _HALF_DAY_LEAVE_POLICY_QUESTION.search(question)
        and not _EXPLICIT_LEAVE_ACTION.search(question)
    ):
        return "policy"

    # Actual requests to submit, approve, reject, or cancel an action
    # continue through the existing classifier.
    return classify_message(question)


def is_explicit_unsafe_sql_request(message: str) -> bool:
    """Detect destructive SQL and explicit natural-language data deletion requests."""
    if not message:
        return False

    # Preserve educational questions about SQL operations.
    if _EXPLANATION_REQUEST.search(message):
        return False

    # Block direct natural-language requests to delete or destroy HRMS data.
    if _NATURAL_LANGUAGE_DESTRUCTIVE_REQUEST.search(message):
        return True

    has_forbidden_keyword = bool(_UNSAFE_SQL_KEYWORDS.search(message))
    if not has_forbidden_keyword:
        return False

    return bool(
        _EXPLICIT_SQL_EXECUTION.search(message)
        or _SQL_LABELLED_DESTRUCTIVE_STATEMENT.search(message)
        or _DIRECT_DESTRUCTIVE_STATEMENT.search(message)
    )
@router.post("/sessions")
async def create_chat_session(
    payload: ChatSessionCreate,
    current_user: Employee = Depends(get_current_user),
):
    _ = payload
    _ = current_user

    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=error_response(
            "CHAT_NOT_IMPLEMENTED",
            "Chat session creation is a Phase-3 stub and not implemented yet",
        ),
    )


@router.post("/sessions/{session_id}/messages")
async def post_chat_message(
    session_id: str,
    payload: ChatMessageCreate,
    current_user: Employee = Depends(get_current_user),
):
    _ = session_id
    _ = payload
    _ = current_user

    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=error_response(
            "CHAT_NOT_IMPLEMENTED",
            "Chat messaging is a Phase-3 stub and not implemented yet",
        ),
    )


@router.post("/sql")
async def sql_chat(
    payload: ChatMessageCreate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    started_at = perf_counter()
    try:
        result = await answer_sql_question(
            db=db,
            user=current_user,
            question=payload.content,
        )

        records_accessed = 0
        if isinstance(result, dict):
            rows = result.get("rows")
            if isinstance(rows, list):
                records_accessed = len(rows)

        await log_ai_interaction(
            user=current_user,
            message=payload.content,
            intent="sql_question",
            tool_name="sql_agent",
            action_status="success",
            records_accessed=records_accessed,
            started_at=started_at,
        )

        return {"success": True, "data": result}

    except PermissionError as exc:
        await log_ai_interaction(
            user=current_user,
            message=payload.content,
            intent="sql_question",
            tool_name="sql_agent",
            action_status="permission_denied",
            records_accessed=0,
            started_at=started_at,
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=error_response("AI_PERMISSION_DENIED", str(exc)),
        )

    except ValueError as exc:
        await log_ai_interaction(
            user=current_user,
            message=payload.content,
            intent="sql_question",
            tool_name="sql_agent",
            action_status="invalid_request",
            records_accessed=0,
            started_at=started_at,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response("AI_SQL_REQUEST_INVALID", str(exc)),
        )


@router.post("/policy")
async def policy_chat(
    payload: ChatMessageCreate,
    current_user: Employee = Depends(get_current_user),
):
    started_at = perf_counter()
    try:
        result = await answer_policy_question(question=payload.content)

        await log_ai_interaction(
            user=current_user,
            message=payload.content,
            intent="policy_question",
            tool_name="policy_rag",
            action_status="success",
            records_accessed=len(result.sources),
            started_at=started_at,
        )

        return {
            "success": True,
            "data": {
                "answer": result.answer,
                "sources": result.sources,
            },
        }

    except ValueError as exc:
        await log_ai_interaction(
            user=current_user,
            message=payload.content,
            intent="policy_question",
            tool_name="policy_rag",
            action_status="invalid_request",
            records_accessed=0,
            started_at=started_at,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response("AI_POLICY_REQUEST_INVALID", str(exc)),
        )


@router.post("/actions")
async def ai_actions_chat(
    payload: ChatMessageCreate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    started_at = perf_counter()
    question = (payload.content or "").strip()

    if not question:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                "AI_MESSAGE_EMPTY",
                "Please enter an HR action request.",
            ),
        )

    try:
        result = await execute_action(
            db=db,
            user=current_user,
            question=question,
        )

        action_status = "success"
        records_accessed = 0

        if isinstance(result, dict):
            action_status = result.get("status", "success")
            details = result.get("details")

            if isinstance(details, dict):
                items = details.get("items")
                if isinstance(items, list):
                    records_accessed = len(items)
                elif isinstance(details.get("balances"), list):
                    records_accessed = len(details["balances"])
                elif isinstance(details.get("id"), int):
                    records_accessed = 1
                elif isinstance(details.get("employee_id"), int):
                    records_accessed = 1

        await log_ai_interaction(
            user=current_user,
            message=question,
            intent="hr_action",
            tool_name="action_agent",
            action_status=action_status,
            records_accessed=records_accessed,
            started_at=started_at,
        )

        return {
            "success": True,
            "data": {"intent": "action", **result},
        }

    except PermissionError as exc:
        await log_ai_interaction(
            user=current_user,
            message=question,
            intent="hr_action",
            tool_name="action_agent",
            action_status="permission_denied",
            records_accessed=0,
            started_at=started_at,
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=error_response("AI_PERMISSION_DENIED", str(exc)),
        )

    except ValueError as exc:
        await log_ai_interaction(
            user=current_user,
            message=question,
            intent="hr_action",
            tool_name="action_agent",
            action_status="invalid_request",
            records_accessed=0,
            started_at=started_at,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response("AI_ACTION_REQUEST_INVALID", str(exc)),
        )

    except HTTPException as exc:
        await log_ai_interaction(
            user=current_user,
            message=question,
            intent="hr_action",
            tool_name="action_agent",
            action_status="backend_rejected",
            records_accessed=0,
            started_at=started_at,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )


def _router_trace_inputs(inputs):
    """Keep only the user's message and role in the parent LangSmith trace."""
    if not isinstance(inputs, dict):
        return {"question": "", "role": ""}

    payload = inputs.get("payload")
    if isinstance(payload, dict):
        question = payload.get("content", "")
        role = payload.get("role", "")
    else:
        question = getattr(payload, "content", "")
        role = getattr(payload, "role", "")

    return {
        "question": str(question or "").strip(),
        "role": str(role or ""),
    }


@traceable(
    name="hrms_chat_request",
    run_type="chain",
    process_inputs=_router_trace_inputs,
    enabled=True,
)
async def _traced_ai_router_chat(
    payload: ChatMessageCreate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    question = (payload.content or "").strip()

    started_at = perf_counter()

    if not question:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response("AI_MESSAGE_EMPTY", "Please enter a message."),
        )

    # Block explicitly requested destructive SQL before semantic routing.
    if is_explicit_unsafe_sql_request(question):
        await log_ai_interaction(
            user=current_user,
            message=question,
            intent="sql_question",
            tool_name="sql_guardrails",
            action_status="blocked_unsafe_sql",
            records_accessed=0,
            started_at=started_at,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                "AI_SQL_REQUEST_INVALID",
                "Request blocked: only safe, read-only SQL queries are permitted.",
            ),
        )
    

    # Personal leave-history lookups must bypass semantic SQL routing.
    # They are read-only HR actions handled by action_agent.py.
    leave_history_request = bool(
        re.search(
            r"\b(show|list|view|find|display|check|get|what)\b",
            question,
            re.IGNORECASE,
        )
        and re.search(
            r"\b(my|me|previous|past|submitted|history)\b",
            question,
            re.IGNORECASE,
        )
        and re.search(
            r"\b(leave requests?|leave applications?|leave history)\b",
            question,
            re.IGNORECASE,
        )
    ) or bool(
        re.search(
            r"\b(leave requests?|leave applications?)\b",
            question,
            re.IGNORECASE,
        )
        and re.search(
            r"\b(last\s+\d+\s+days?|last month|recent|previous)\b",
            question,
            re.IGNORECASE,
        )
    )

    intent = (
        "action"
        if leave_history_request
        else classify_copilot_intent(question)
    )
    if intent == "policy":
        try:
            result = await run_hrms_graph(
                question=question,
                db=db,
                user=current_user,
                intent=intent,
            )

            await log_ai_interaction(
                user=current_user,
                message=question,
                intent="policy_question",
                tool_name="policy_rag",
                action_status="success",
                records_accessed=len(result.sources),
                started_at=started_at,
            )
            return {
                "success": True,
                "data": {
                    "intent": "policy",
                    "answer": result.answer,
                    "sources": result.sources,
                },
            }

        except ValueError as exc:
            await log_ai_interaction(
                user=current_user,
                message=question,
                intent="policy_question",
                tool_name="policy_rag",
                action_status="invalid_request",
                records_accessed=0,
                started_at=started_at,
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response("AI_POLICY_REQUEST_INVALID", str(exc)),
            )

    if intent == "sql":
        try:
            result = await run_hrms_graph(
                question=question,
                db=db,
                user=current_user,
                intent=intent,
            )

            rows = result.get("rows", []) if isinstance(result, dict) else []
            records_accessed = len(rows) if isinstance(rows, list) else 0

            await log_ai_interaction(
                user=current_user,
                message=question,
                intent="sql_question",
                tool_name="sql_agent",
                action_status="success",
                records_accessed=records_accessed,
                started_at=started_at,
            )
            return {
                "success": True,
                "data": {"intent": "sql", **result},
            }

        except PermissionError as exc:
            await log_ai_interaction(
                user=current_user,
                message=question,
                intent="sql_question",
                tool_name="sql_agent",
                action_status="permission_denied",
                records_accessed=0,
                started_at=started_at,
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=error_response("AI_PERMISSION_DENIED", str(exc)),
            )

        except ValueError as exc:
            await log_ai_interaction(
                user=current_user,
                message=question,
                intent="sql_question",
                tool_name="sql_agent",
                action_status="invalid_request",
                records_accessed=0,
                started_at=started_at,
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response("AI_SQL_REQUEST_INVALID", str(exc)),
            )

    if intent == "action":
        try:
            result = await run_hrms_graph(
                question=question,
                db=db,
                user=current_user,
                intent=intent,
            )

            action_status = "success"
            records_accessed = 0

            if isinstance(result, dict):
                action_status = result.get("status", "success")
                details = result.get("details")

                if isinstance(details, dict):
                    items = details.get("items")
                    if isinstance(items, list):
                        records_accessed = len(items)
                    elif isinstance(details.get("balances"), list):
                        records_accessed = len(details["balances"])
                    elif isinstance(details.get("id"), int):
                        records_accessed = 1
                    elif isinstance(details.get("employee_id"), int):
                        records_accessed = 1

            await log_ai_interaction(
                user=current_user,
                message=question,
                intent="hr_action",
                tool_name="action_agent",
                action_status=action_status,
                records_accessed=records_accessed,
                started_at=started_at,
            )
            return {
                "success": True,
                "data": {"intent": "action", **result},
            }

        except PermissionError as exc:
            await log_ai_interaction(
                user=current_user,
                message=question,
                intent="hr_action",
                tool_name="action_agent",
                action_status="permission_denied",
                records_accessed=0,
                started_at=started_at,
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=error_response("AI_PERMISSION_DENIED", str(exc)),
            )

        except ValueError as exc:
            await log_ai_interaction(
                user=current_user,
                message=question,
                intent="hr_action",
                tool_name="action_agent",
                action_status="invalid_request",
                records_accessed=0,
                started_at=started_at,
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response("AI_ACTION_REQUEST_INVALID", str(exc)),
            )

        except HTTPException as exc:
            await log_ai_interaction(
                user=current_user,
                message=question,
                intent="hr_action",
                tool_name="action_agent",
                action_status="backend_rejected",
                records_accessed=0,
                started_at=started_at,
            )
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
            )

    await log_ai_interaction(
        user=current_user,
        message=question,
        intent="unknown",
        tool_name="semantic_router",
        action_status="unsupported",
        records_accessed=0,
        started_at=started_at,
    )
    return {
        "success": True,
        "data": {
            "intent": "unknown",
            "status": "unsupported",
            "answer": (
                "I can help with HR policies, HRMS data, "
                "and supported HR tasks. Please ask an HR-related question."
            ),
        },
    }


@router.post("/actions/confirmations/{confirmation_id}/confirm")
async def confirm_hr_action(
    confirmation_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm and execute a pending high-impact action exactly once."""
    try:
        confirmation = await claim_confirmation(db=db, user=current_user, token=confirmation_id)
    except LookupError as exc:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=error_response("HITL_CONFIRMATION_NOT_FOUND", str(exc)))
    except TimeoutError as exc:
        return JSONResponse(status_code=status.HTTP_410_GONE, content=error_response("HITL_CONFIRMATION_EXPIRED", str(exc)))
    except RuntimeError as exc:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=error_response("HITL_CONFIRMATION_ALREADY_USED", str(exc)))

    try:
        result = await execute_action(db=db, user=current_user, question=confirmation.question, confirmed=True)
        succeeded = not (isinstance(result, dict) and result.get("status") in {"unsupported", "denied", "error"})
        await finish_confirmation(
            db, confirmation, success=succeeded,
            error_message=None if succeeded else str(result.get("answer", "Action was not completed.")),
        )
        if not succeeded:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"success": False, "data": result})
        return {"success": True, "data": {"intent": "action", **result}}
    except PermissionError as exc:
        await finish_confirmation(db, confirmation, success=False, error_message=str(exc))
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=error_response("AI_PERMISSION_DENIED", str(exc)))
    except ValueError as exc:
        await finish_confirmation(db, confirmation, success=False, error_message=str(exc))
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response("AI_ACTION_REQUEST_INVALID", str(exc)))
    except HTTPException as exc:
        await finish_confirmation(db, confirmation, success=False, error_message=str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    except Exception as exc:
        await finish_confirmation(db, confirmation, success=False, error_message=type(exc).__name__)
        raise


@router.post("/actions/confirmations/{confirmation_id}/cancel")
async def cancel_hr_action(
    confirmation_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending action without executing it."""
    try:
        await cancel_confirmation(db=db, user=current_user, token=confirmation_id)
    except LookupError as exc:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=error_response("HITL_CONFIRMATION_NOT_FOUND", str(exc)))
    except RuntimeError as exc:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=error_response("HITL_CONFIRMATION_ALREADY_USED", str(exc)))
    return {"success": True, "data": {"status": "canceled", "answer": "The action was canceled. No change was made."}}


@router.post("/router")
async def ai_router_chat(
    payload: ChatMessageCreate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Preserve FastAPI's explicit endpoint signature while tracing router work."""
    return await _traced_ai_router_chat(
        payload=payload,
        current_user=current_user,
        db=db,
    )

@router.post("/router/stream")
async def ai_router_chat_stream(
    payload: ChatMessageCreate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream policy answers while preserving existing routing for other intents."""

    question = (payload.content or "").strip()

    if not question:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                "AI_REQUEST_INVALID",
                "Please enter a question.",
            ),
        )

    intent = classify_copilot_intent(question)

    # Only policy responses use the token-by-token streaming path.
    # Delegate every other intent to the existing router exactly once.
    if intent != "policy":
        result = await _traced_ai_router_chat(
            payload=payload,
            current_user=current_user,
            db=db,
        )

        async def emit_existing_result():
            if isinstance(result, JSONResponse):
                yield (
                    "event: error\n"
                    f"data: {result.body.decode('utf-8')}\n\n"
                )
                return

            yield (
                "event: result\n"
                f"data: {json.dumps(result, default=str)}\n\n"
            )

        return StreamingResponse(
            emit_existing_result(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @traceable(
        name="hrms_chat_request",
        run_type="chain",
        process_inputs=lambda _inputs: {
            "question": question,
            "role": getattr(payload, "role", "user"),
        },
        enabled=True,
    )
    async def policy_event_stream():
        started_at = perf_counter()
        sources_count = 0
        action_status = "success"

        try:
            async for event in stream_policy_answer(question):
                if event.get("type") == "sources":
                    sources_count = len(event.get("sources", []))

                if event.get("type") == "error":
                    action_status = "error"

                yield f"data: {json.dumps(event, default=str)}\n\n"

            await log_ai_interaction(
                user=current_user,
                message=question,
                intent="policy_question",
                tool_name="policy_rag",
                action_status=action_status,
                records_accessed=sources_count,
                started_at=started_at,
            )

        except Exception:
            await log_ai_interaction(
                user=current_user,
                message=question,
                intent="policy_question",
                tool_name="policy_rag",
                action_status="error",
                records_accessed=sources_count,
                started_at=started_at,
            )

            yield (
                "data: "
                + json.dumps({
                    "type": "error",
                    "message": (
                        "Something went wrong while streaming the response. "
                        "Please try again."
                    ),
                })
                + "\n\n"
            )

    return StreamingResponse(
        policy_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
