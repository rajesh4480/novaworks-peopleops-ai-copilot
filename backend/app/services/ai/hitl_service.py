from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.hitl_confirmation import PendingActionConfirmation

CONFIRMATION_TTL_MINUTES = 10

# These patterns intentionally target mutating requests, not read-only queries.
_HIGH_IMPACT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "leave_decision",
        re.compile(r"\b(?:approve|accept|reject|decline)\b.*\b(?:leave request|leave)\b", re.I),
    ),
    (
        "project_assignment",
        re.compile(r"\b(?:assign|allocate)\b.*\b(?:employee|staff)\s*(?:id\s*)?#?\d+.*\bproject\s*(?:id\s*)?#?\d+", re.I),
    ),
    (
        "announcement_creation",
        re.compile(r"\b(?:create|post|publish)\b.*\bannouncement\b", re.I),
    ),
    (
        "ticket_status_update",
        re.compile(r"\b(?:update|change|set|mark|resolve|close)\b.*\bticket\b", re.I),
    ),
)


def _utcnow_naive() -> datetime:
    # SQLite commonly returns timezone-naive values even for timezone=True.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _role_value(user: Employee) -> str:
    return str(getattr(user.role, "value", user.role)).upper()


def _status_value(user: Employee) -> str:
    return str(getattr(user.status, "value", user.status)).upper()


def identify_high_impact_action(question: str) -> str | None:
    text = (question or "").strip()
    if not text:
        return None
    for action_type, pattern in _HIGH_IMPACT_PATTERNS:
        if pattern.search(text):
            return action_type
    return None


async def request_confirmation_if_required(
    db: AsyncSession, user: Employee, question: str
) -> dict | None:
    """Persist a pending confirmation; return None for ordinary low-risk actions."""
    action_type = identify_high_impact_action(question)
    if action_type is None:
        return None

    if _status_value(user) != "ACTIVE":
        raise PermissionError("Only active employees can request HR actions.")
    if _role_value(user) not in {"MANAGER", "ADMIN"}:
        raise PermissionError("Only managers or admins can perform this high-impact action.")

    now = _utcnow_naive()
    token = str(uuid4())
    record = PendingActionConfirmation(
        token=token,
        user_id=user.id,
        action_type=action_type,
        question=question.strip(),
        status="pending",
        created_at=now,
        expires_at=now + timedelta(minutes=CONFIRMATION_TTL_MINUTES),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "status": "confirmation_required",
        "answer": (
            "This action can affect HR records. Please confirm or cancel it "
            f"within {CONFIRMATION_TTL_MINUTES} minutes. No change has been made yet."
        ),
        "confirmation": {
            "id": record.token,
            "action_type": record.action_type,
            "request": record.question,
            "expires_at": record.expires_at.isoformat() + "Z",
            "confirm_endpoint": f"/api/v1/chat/actions/confirmations/{record.token}/confirm",
            "cancel_endpoint": f"/api/v1/chat/actions/confirmations/{record.token}/cancel",
        },
    }


async def claim_confirmation(
    db: AsyncSession, user: Employee, token: str
) -> PendingActionConfirmation:
    """Atomically claim a pending, unexpired confirmation for this user once."""
    now = _utcnow_naive()
    result = await db.execute(
        select(PendingActionConfirmation).where(
            PendingActionConfirmation.token == token,
            PendingActionConfirmation.user_id == user.id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise LookupError("Confirmation was not found for your account.")
    if record.status != "pending":
        raise RuntimeError(f"This confirmation is already {record.status} and cannot be reused.")
    if record.expires_at <= now:
        record.status = "expired"
        await db.commit()
        raise TimeoutError("This confirmation has expired. Please submit the action again.")

    claimed = await db.execute(
        update(PendingActionConfirmation)
        .where(
            PendingActionConfirmation.token == token,
            PendingActionConfirmation.user_id == user.id,
            PendingActionConfirmation.status == "pending",
            PendingActionConfirmation.expires_at > now,
        )
        .values(status="executing", confirmed_at=now)
    )
    if claimed.rowcount != 1:
        await db.rollback()
        raise RuntimeError("This confirmation has already been used or has expired.")
    await db.commit()
    await db.refresh(record)
    return record


async def cancel_confirmation(db: AsyncSession, user: Employee, token: str) -> None:
    now = _utcnow_naive()
    result = await db.execute(
        select(PendingActionConfirmation).where(
            PendingActionConfirmation.token == token,
            PendingActionConfirmation.user_id == user.id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise LookupError("Confirmation was not found for your account.")
    if record.status != "pending":
        raise RuntimeError(f"This confirmation is already {record.status} and cannot be canceled.")
    record.status = "canceled" if record.expires_at > now else "expired"
    await db.commit()


async def finish_confirmation(
    db: AsyncSession,
    record: PendingActionConfirmation,
    *,
    success: bool,
    error_message: str | None = None,
) -> None:
    # A claimed confirmation is never reset to pending: retries cannot replay it.
    result = await db.execute(
        select(PendingActionConfirmation).where(
            PendingActionConfirmation.id == record.id,
            PendingActionConfirmation.status == "executing",
        )
    )
    current = result.scalar_one_or_none()
    if current is None:
        return
    current.status = "completed" if success else "failed"
    current.completed_at = _utcnow_naive()
    current.error_message = error_message[:2000] if error_message else None
    await db.commit()
