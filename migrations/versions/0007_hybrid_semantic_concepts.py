"""Add isolated HYBRID-001 semantic concept shadow storage."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_hybrid_semantic_concepts"
down_revision = "0006_auth_rate_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "semantic_concept_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("extractor_version", sa.String(128), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(256), nullable=False),
        sa.Column("model_digest", sa.String(128), nullable=False),
        sa.Column("config_json", postgresql.JSONB(), nullable=False),
        sa.Column("snapshot_json", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('running','completed','failed')", name="ck_semantic_concept_runs_status"
        ),
    )
    op.create_table(
        "technical_concepts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("concept_type", sa.String(32), nullable=False),
        sa.Column("canonical_name", sa.String(256), nullable=False),
        sa.Column("normalized_key", sa.String(320), nullable=False, unique=True),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "concept_type IN ("
            "'MATERIAL','DEVICE','PROPERTY','PERFORMANCE','ANALYTE','PROCESS','MECHANISM',"
            "'OPERATING_CONDITION','MORPHOLOGY','TECHNOLOGY','APPLICATION','OTHER')",
            name="ck_technical_concepts_type",
        ),
    )
    op.create_table(
        "concept_mentions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("semantic_concept_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "concept_id",
            sa.String(64),
            sa.ForeignKey("technical_concepts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("source_documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("surface_text", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("qualifiers_json", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("extractor_version", sa.String(128), nullable=False),
        sa.Column("model_id", sa.String(256), nullable=False),
        sa.Column("model_digest", sa.String(128), nullable=False),
        sa.ForeignKeyConstraint(
            ["revision_id", "document_id"],
            ["document_revisions.id", "document_revisions.document_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id", "revision_id"],
            ["evidence_chunks.id", "evidence_chunks.revision_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "start_offset >= 0 AND end_offset > start_offset", name="ck_concept_mentions_span"
        ),
        sa.UniqueConstraint("id", "run_id", name="uq_concept_mentions_id_run"),
    )
    op.create_index(
        "ix_concept_mentions_run_document", "concept_mentions", ["run_id", "document_id"]
    )
    op.create_index("ix_concept_mentions_run_concept", "concept_mentions", ["run_id", "concept_id"])
    op.create_table(
        "semantic_concept_run_documents",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("run_id", "document_id"),
        sa.ForeignKeyConstraint(["run_id"], ["semantic_concept_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["revision_id", "document_id"],
            ["document_revisions.id", "document_revisions.document_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('pending','completed','failed')",
            name="ck_semantic_concept_run_documents_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("semantic_concept_run_documents")
    op.drop_index("ix_concept_mentions_run_concept", table_name="concept_mentions")
    op.drop_index("ix_concept_mentions_run_document", table_name="concept_mentions")
    op.drop_table("concept_mentions")
    op.drop_table("technical_concepts")
    op.drop_table("semantic_concept_runs")
