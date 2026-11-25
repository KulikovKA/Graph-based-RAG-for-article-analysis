"""Добавить согласие на внешний контекст по запуску."""

import sqlalchemy as sa
from alembic import op

revision = "0008_external_consents"
down_revision = "0007_hybrid_semantic_concepts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_consents",
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("notice_version", sa.String(64), nullable=False),
        sa.Column("revision", sa.Uuid(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("external_consents")
