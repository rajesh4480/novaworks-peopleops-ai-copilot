
from __future__ import annotations

import asyncio
import re
from time import perf_counter

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.db.session import SessionLocal
from app.models.ai_audit_log import AIAuditLog
from app.models.employee import Employee


_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Email addresses
    (
        re.compile(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            re.IGNORECASE,
        ),
        "[REDACTED_EMAIL]",
    ),
    # Common Indian PAN format
    (
        re.compile(
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
            re.IGNORECASE,
        ),
        "[REDACTED_PAN]",
    ),
    # Labeled credentials and secrets
    (
        re.compile(
            r"\b(password|passwd|api[ _-]?key|access[ _-]?token|"
            r"refresh[ _-]?token|secret)\b"
            r"(\s*[:=]\s*|\s+)([^\s,;]+)",
            re.IGNORECASE,
        ),
        r"\1\2[REDACTED]",
    ),
    # Labeled bank account numbers
    (
        re.compile(
            r"\b(bank account(?: number)?|account number|account no\.?)"
            r"(\s*[:=]\s*|\s+)([0-9][0-9 -]{5,}[0-9])",
            re.IGNORECASE,
        ),
        r"\1\2[REDACTED_ACCOUNT]",
    ),
    # Aadhaar-like 12-digit numbers, including spaced or hyphenated forms
    (
        re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
        "[REDACTED_ID_NUMBER]",
    ),
)


def _redact_audit_message(message: str) -> str:
    """Redact common sensitive values before storing an audit message."""
    sanitized = message

    for pattern, replacement in _REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


async def log_ai_interaction(
    *,
    user: Employee,
    message: str,
    intent: str,
    tool_name: str,
    action_status: str,
    records_accessed: int = 0,
    latency_ms: float | None = None,
    started_at: float | None = None,
) -> None:
    """
    Persist AI interaction metadata with message redaction and optional latency.

    Audit logging is best-effort so a temporary SQLite lock does not crash
    the chat request. Transient SQLite locking errors are retried.
    """

    if started_at is not None:
        latency_ms = max(0.0, (perf_counter() - started_at) * 1000.0)

    audit_log = AIAuditLog(
        user_id=user.id,
        role=user.role.value,
        message=_redact_audit_message(message),
        intent=intent,
        tool_name=tool_name,
        action_status=action_status,
        records_accessed=max(0, records_accessed),
        latency_ms=(
            max(0.0, latency_ms)
            if latency_ms is not None
            else None
        ),
    )

    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            async with SessionLocal() as session:
                session.add(audit_log)
                await session.commit()

            return

        except OperationalError as exc:
            error_message = str(exc).lower()

            is_locked = (
                "database is locked" in error_message
                or "database table is locked" in error_message
            )

            if not is_locked:
                print(f"AI audit logging database error: {exc}")
                return

            if attempt < max_attempts - 1:
                await asyncio.sleep(0.2 * (attempt + 1))
            else:
                print(
                    "AI audit logging skipped after repeated SQLite "
                    f"lock errors: {exc}"
                )

        except SQLAlchemyError as exc:
            print(f"AI audit logging failed: {exc}")
            return
