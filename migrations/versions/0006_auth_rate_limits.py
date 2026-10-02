"""Общие лимиты запросов AUTH-001."""

import sqlalchemy as sa
from alembic import op

revision = "0006_auth_rate_limits"
down_revision = "0005_graph002_shadow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_rate_limits",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("window_no", sa.BigInteger(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("auth_rate_limits")
