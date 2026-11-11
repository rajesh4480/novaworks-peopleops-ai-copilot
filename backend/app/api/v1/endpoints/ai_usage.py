from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.session import get_db
from app.models.ai_audit_log import AIAuditLog
from app.models.employee import Employee
from app.models.enums import Role
from app.services.auth import require_roles


router = APIRouter(prefix="/ai-usage", tags=["AI Usage"])

# These values match the current chat handlers:
# SQL: tool_name="sql_agent", action_status="invalid_request"/"permission_denied"
# RAG: tool_name="policy_rag", with records_accessed tracking retrieved sources.
_PERMISSION_FAILURE_STATUSES = {"permission_denied"}
_SQL_BLOCKED_STATUSES = {
    "blocked",
    "invalid_request",
    "permission_denied",
    "sql_blocked",
}


@router.get("/analytics")
async def get_ai_usage_analytics(
    _: Employee = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregate AI usage metrics for administrators only."""
    result = await db.execute(
        select(
            AIAuditLog.intent,
            AIAuditLog.tool_name,
            AIAuditLog.action_status,
            AIAuditLog.records_accessed,
            AIAuditLog.latency_ms,
        )
    )
    rows = result.all()

    total_requests = len(rows)
    intent_counts = Counter(row.intent for row in rows if row.intent)
    tool_counts = Counter(row.tool_name for row in rows if row.tool_name)

    failed_permission_attempts = sum(
        1
        for row in rows
        if (row.action_status or "").lower() in _PERMISSION_FAILURE_STATUSES
    )

    latencies = [
        float(row.latency_ms)
        for row in rows
        if row.latency_ms is not None and float(row.latency_ms) >= 0
    ]
    average_latency_ms = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    rag_rows = [
        row for row in rows
        if (row.tool_name or "").lower() == "policy_rag"
        and (row.action_status or "").lower() not in {"invalid_request"}
    ]
    rag_no_answer_count = sum(
        1 for row in rag_rows if (row.records_accessed or 0) == 0
    )
    rag_no_answer_rate = (
        round(rag_no_answer_count / len(rag_rows), 4) if rag_rows else 0.0
    )

    sql_blocked_queries = sum(
        1
        for row in rows
        if (row.tool_name or "").lower() == "sql_agent"
        and (row.action_status or "").lower() in _SQL_BLOCKED_STATUSES
    )

    return success_response(
        {
            "total_requests": total_requests,
            "most_common_intents": [
                {"intent": name, "count": count}
                for name, count in intent_counts.most_common(10)
            ],
            "failed_permission_attempts": failed_permission_attempts,
            "most_used_tools": [
                {"tool": name, "count": count}
                for name, count in tool_counts.most_common(10)
            ],
            "average_latency_ms": average_latency_ms,
            "rag_no_answer_rate": rag_no_answer_rate,
            "rag_no_answer_count": rag_no_answer_count,
            "rag_requests_counted": len(rag_rows),
            "sql_blocked_queries": sql_blocked_queries,
        }
    )
