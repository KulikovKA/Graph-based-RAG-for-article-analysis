"""Постоянные подтверждения для независимых потребителей outbox."""

import sqlalchemy as sa
from alembic import op

revision = "0002_outbox_acks"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_acks",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("consumer", sa.String(128), nullable=False),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["outbox_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id", "consumer"),
    )


def downgrade() -> None:
    op.drop_table("outbox_acks")
