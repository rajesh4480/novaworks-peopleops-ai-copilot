from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIAuditLog(Base):
    __tablename__ = "ai_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"),
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(30),
        index=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
    )

    intent: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    tool_name: Mapped[str] = mapped_column(
        String(100),
        index=True,
    )

    action_status: Mapped[str] = mapped_column(
        String(30),
        index=True,
    )

    records_accessed: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    latency_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
