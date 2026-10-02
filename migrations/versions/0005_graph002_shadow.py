"""Add isolated GRAPH-002 canonicalization storage."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_graph002_shadow"
down_revision = "0004_run_publication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "canonicalization_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resolver_version", sa.String(128), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("embedding_model_id", sa.String(256), nullable=False),
        sa.Column("embedding_model_digest", sa.String(128), nullable=False),
        sa.Column("classifier_model_id", sa.String(256), nullable=False),
        sa.Column("classifier_model_digest", sa.String(128), nullable=False),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('running','completed','failed')", name="ck_canonicalization_runs_status"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_canonicalization_runs_snapshot", "canonicalization_runs", ["snapshot_hash"])
    op.create_table(
        "canonical_features",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_text", sa.Text(), nullable=False),
        sa.Column("canonical_key", sa.String(64), nullable=False),
        sa.Column("member_count", sa.Integer(), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("member_count >= 1", name="ck_canonical_features_member_count"),
        sa.CheckConstraint("document_count >= 1", name="ck_canonical_features_document_count"),
        sa.ForeignKeyConstraint(["run_id"], ["canonicalization_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "canonical_key", name="uq_canonical_features_run_key"),
        sa.UniqueConstraint("run_id", "id", name="uq_canonical_features_run_id"),
    )
    op.create_index("ix_canonical_features_run", "canonical_features", ["run_id"])
    op.create_table(
        "feature_pair_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("feature_a_key", sa.String(768), nullable=False),
        sa.Column("feature_b_key", sa.String(768), nullable=False),
        sa.Column("candidate_similarity", sa.Float(), nullable=False),
        sa.Column("classifier_decision", sa.String(16), nullable=False),
        sa.Column("probabilities_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("classifier_confidence", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "classifier_decision IN ('SAME','DIFFERENT','UNCERTAIN')",
            name="ck_feature_pair_decisions_label",
        ),
        sa.CheckConstraint(
            "candidate_similarity >= -1 AND candidate_similarity <= 1",
            name="ck_feature_pair_decisions_similarity",
        ),
        sa.CheckConstraint(
            "classifier_confidence >= 0 AND classifier_confidence <= 1",
            name="ck_feature_pair_decisions_confidence",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["canonicalization_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id", "feature_a_key", "feature_b_key", name="uq_feature_pair_decisions_pair"
        ),
    )
    op.create_index("ix_feature_pair_decisions_run", "feature_pair_decisions", ["run_id"])
    op.create_table(
        "feature_resolutions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("graph_fact_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_feature_id", sa.Uuid(), nullable=False),
        sa.Column("raw_feature_text", sa.Text(), nullable=False),
        sa.Column("normalized_feature_text", sa.Text(), nullable=False),
        sa.Column("resolution_method", sa.String(24), nullable=False),
        sa.Column("candidate_similarity", sa.Float(), nullable=True),
        sa.Column("classifier_decision", sa.String(16), nullable=True),
        sa.Column("probabilities_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("classifier_confidence", sa.Float(), nullable=True),
        sa.Column("resolver_version", sa.String(128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "resolution_method IN ('exact','normalized_exact','tev1_same','new_singleton')",
            name="ck_feature_resolutions_method",
        ),
        sa.CheckConstraint(
            "classifier_decision IS NULL OR classifier_decision IN "
            "('SAME','DIFFERENT','UNCERTAIN')",
            name="ck_feature_resolutions_classifier_label",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "canonical_feature_id"],
            ["canonical_features.run_id", "canonical_features.id"],
            ondelete="CASCADE",
            name="fk_feature_resolutions_run_canonical_feature",
        ),
        sa.ForeignKeyConstraint(["graph_fact_id"], ["graph_facts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id"], ["canonicalization_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "graph_fact_id", name="uq_feature_resolutions_run_fact"),
    )
    op.create_index(
        "ix_feature_resolutions_run_feature",
        "feature_resolutions",
        ["run_id", "canonical_feature_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_feature_resolutions_run_feature", table_name="feature_resolutions")
    op.drop_table("feature_resolutions")
    op.drop_index("ix_feature_pair_decisions_run", table_name="feature_pair_decisions")
    op.drop_table("feature_pair_decisions")
    op.drop_index("ix_canonical_features_run", table_name="canonical_features")
    op.drop_table("canonical_features")
    op.drop_index("ix_canonicalization_runs_snapshot", table_name="canonicalization_runs")
    op.drop_table("canonicalization_runs")
