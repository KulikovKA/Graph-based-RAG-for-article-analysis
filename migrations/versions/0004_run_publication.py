"""Add durable result projections and progress snapshots for ADR-011 runs."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_run_publication"
down_revision = "0003_graph_fact_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analysis_runs", sa.Column("analysis_json", postgresql.JSONB(), nullable=True))
    op.add_column(
        "analysis_runs", sa.Column("public_analysis_json", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "analysis_runs", sa.Column("answer_presentation_json", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "analysis_runs",
        sa.Column(
            "progress_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("legacy_projection", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_check_constraint(
        "ck_runs_publication_projections",
        "analysis_runs",
        "legacy_projection OR status <> 'completed' OR "
        "(answer_json IS NOT NULL AND public_analysis_json IS NOT NULL "
        "AND answer_presentation_json IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_runs_analysis_projection",
        "analysis_runs",
        "legacy_projection OR outcome <> 'analysis' OR analysis_json IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_runs_nonterminal_projections",
        "analysis_runs",
        "status = 'completed' OR (analysis_json IS NULL AND public_analysis_json IS NULL "
        "AND answer_presentation_json IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_runs_nonterminal_projections", "analysis_runs", type_="check")
    op.drop_constraint("ck_runs_analysis_projection", "analysis_runs", type_="check")
    op.drop_constraint("ck_runs_publication_projections", "analysis_runs", type_="check")
    op.drop_column("analysis_runs", "legacy_projection")
    op.drop_column("analysis_runs", "progress_json")
    op.drop_column("analysis_runs", "answer_presentation_json")
    op.drop_column("analysis_runs", "public_analysis_json")
    op.drop_column("analysis_runs", "analysis_json")
