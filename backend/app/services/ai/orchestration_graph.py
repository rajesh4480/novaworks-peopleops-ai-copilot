from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.ai.action_agent import execute_action
from app.services.ai.policy_rag_service import answer_policy_question
from app.services.ai.router import classify_message
from app.services.ai.sql_service import answer_sql_question


class HRMSGraphState(TypedDict, total=False):
    """State passed between the HRMS agent orchestration nodes."""

    question: str
    db: Any
    user: Any
    intent: str
    result: Any


def _normalize_intent(intent: str) -> str:
    """Normalize existing router labels into graph destinations."""

    value = intent.strip().lower().replace("-", "_").replace(" ", "_")

    aliases = {
        "policy_rag": "policy",
        "hr_policy": "policy",
        "policies": "policy",
        "sql_agent": "sql",
        "database": "sql",
        "action_agent": "action",
        "hr_action": "action",
        "hr_task_automation": "action",
    }

    return aliases.get(value, value)


async def classify_node(state: HRMSGraphState) -> dict:
    """Reuse the existing intent classifier unless intent was supplied."""

    existing_intent = state.get("intent")

    if existing_intent:
        intent = _normalize_intent(existing_intent)
    else:
        intent = _normalize_intent(
            classify_message(state["question"])
        )

    return {"intent": intent}


def route_to_agent(state: HRMSGraphState) -> str:
    """Select the appropriate existing agent."""

    intent = _normalize_intent(state.get("intent", "unknown"))

    if intent == "policy":
        return "policy"

    if intent == "sql":
        return "sql"

    if intent == "action":
        return "action"

    return "unknown"


async def policy_node(state: HRMSGraphState) -> dict:
    """Run the existing Policy RAG service."""

    result = await answer_policy_question(
        question=state["question"],
    )

    return {"result": result}


async def sql_node(state: HRMSGraphState) -> dict:
    """Run the existing read-only SQL service."""

    result = await answer_sql_question(
        db=state["db"],
        user=state["user"],
        question=state["question"],
    )

    return {"result": result}


async def action_node(state: HRMSGraphState) -> dict:
    """Run the existing HR Task Automation Agent."""

    result = await execute_action(
        db=state["db"],
        user=state["user"],
        question=state["question"],
    )

    return {"result": result}


async def unknown_node(state: HRMSGraphState) -> dict:
    """Handle questions that don't match a supported agent."""

    return {
        "result": {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_INTENT",
                "message": (
                    "I couldn't determine which HRMS capability "
                    "can handle this request. Please rephrase it."
                ),
            },
        }
    }


def build_hrms_graph():
    """Build and compile the HRMS multi-agent graph."""

    graph = StateGraph(HRMSGraphState)

    graph.add_node("classify", classify_node)
    graph.add_node("policy", policy_node)
    graph.add_node("sql", sql_node)
    graph.add_node("action", action_node)
    graph.add_node("unknown", unknown_node)

    graph.add_edge(START, "classify")

    graph.add_conditional_edges(
        "classify",
        route_to_agent,
        {
            "policy": "policy",
            "sql": "sql",
            "action": "action",
            "unknown": "unknown",
        },
    )

    graph.add_edge("policy", END)
    graph.add_edge("sql", END)
    graph.add_edge("action", END)
    graph.add_edge("unknown", END)

    return graph.compile()


hrms_graph = build_hrms_graph()


async def run_hrms_graph(
    question: str,
    db: Any,
    user: Any,
    intent: str | None = None,
) -> Any:
    """Run the graph and return the selected agent's result."""

    question = question.strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    initial_state: HRMSGraphState = {
        "question": question,
        "db": db,
        "user": user,
    }

    if intent:
        initial_state["intent"] = intent

    final_state = await hrms_graph.ainvoke(initial_state)

    return final_state["result"]