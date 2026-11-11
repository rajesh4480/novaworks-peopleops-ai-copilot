
"""add AI audit latency

Revision ID: bdfc4f3d0ad9
Revises: 0018_pending_action_confirmations
Create Date: 2026-10-28 20:40:23.285550
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bdfc4f3d0ad9"
down_revision: Union[str, Sequence[str], None] = "0018_pending_action_confirmations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add latency tracking to AI audit logs."""
    op.add_column(
        "ai_audit_logs",
        sa.Column("latency_ms", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Remove latency tracking from AI audit logs."""
    op.drop_column("ai_audit_logs", "latency_ms")
