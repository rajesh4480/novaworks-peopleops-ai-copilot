"""add persistent HITL action confirmations

Revision ID: 0018_pending_action_confirmations
Revises: 0017_ai_audit_logs
Create Date: 2026-10-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018_pending_action_confirmations"
down_revision: Union[str, None] = "0017_ai_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_action_confirmations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_pending_action_confirmations_id", "pending_action_confirmations", ["id"])
    op.create_index("ix_pending_action_confirmations_token", "pending_action_confirmations", ["token"], unique=True)
    op.create_index("ix_pending_action_confirmations_user_id", "pending_action_confirmations", ["user_id"])
    op.create_index("ix_pending_action_confirmations_status", "pending_action_confirmations", ["status"])
    op.create_index("ix_pending_action_confirmations_user_status", "pending_action_confirmations", ["user_id", "status"])
    op.create_index("ix_pending_action_confirmations_expires_at", "pending_action_confirmations", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_pending_action_confirmations_expires_at", table_name="pending_action_confirmations")
    op.drop_index("ix_pending_action_confirmations_user_status", table_name="pending_action_confirmations")
    op.drop_index("ix_pending_action_confirmations_status", table_name="pending_action_confirmations")
    op.drop_index("ix_pending_action_confirmations_user_id", table_name="pending_action_confirmations")
    op.drop_index("ix_pending_action_confirmations_token", table_name="pending_action_confirmations")
    op.drop_index("ix_pending_action_confirmations_id", table_name="pending_action_confirmations")
    op.drop_table("pending_action_confirmations")
