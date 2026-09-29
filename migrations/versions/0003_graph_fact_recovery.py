"""Сохраняет logical identity фактов и маркеры пустого извлечения графа."""

import hashlib
import json

import sqlalchemy as sa
from alembic import op

revision = "0003_graph_fact_recovery"
down_revision = "0002_outbox_acks"
branch_labels = None
depends_on = None


def _logical_key(row: sa.RowMapping, provenance_key: str) -> str:
    payload = {
        "revision_id": str(row["revision_id"]),
        "from_key": row["from_key"],
        "edge_type": row["edge_type"],
        "to_key": row["to_key"],
        "provenance_key": provenance_key,
        "extractor_version": row["extractor_version"],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def upgrade() -> None:
    op.add_column("graph_facts", sa.Column("provenance_key", sa.String(768), nullable=True))
    op.add_column("graph_facts", sa.Column("logical_key_hash", sa.String(64), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, revision_id, from_key, edge_type, to_key, chunk_id, span_start, "
            "span_end, metadata_pointer, extractor_version FROM graph_facts ORDER BY id"
        )
    ).mappings()
    seen: set[str] = set()
    for row in rows:
        if row["chunk_id"] is not None:
            provenance_key = f"chunk:{row['chunk_id']}:{row['span_start']}:{row['span_end']}"
        elif row["metadata_pointer"] is not None:
            pointer = json.dumps(
                row["metadata_pointer"],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            provenance_key = f"metadata:{pointer}"
        else:
            provenance_key = f"legacy:{row['id']}"
        if len(provenance_key) > 768:
            provenance_key = (
                f"metadata-sha256:{hashlib.sha256(provenance_key.encode()).hexdigest()}"
            )
        logical_hash = _logical_key(row, provenance_key)
        if logical_hash in seen:
            # Preserve any pre-existing duplicate facts while keeping the new key unique.
            provenance_key = f"{provenance_key}:legacy:{row['id']}"
            logical_hash = _logical_key(row, provenance_key)
        seen.add(logical_hash)
        connection.execute(
            sa.text(
                "UPDATE graph_facts SET provenance_key = :provenance_key, "
                "logical_key_hash = :logical_key_hash WHERE id = :id"
            ),
            {
                "id": row["id"],
                "provenance_key": provenance_key,
                "logical_key_hash": logical_hash,
            },
        )

    op.alter_column("graph_facts", "provenance_key", nullable=False)
    op.alter_column("graph_facts", "logical_key_hash", nullable=False)
    op.create_unique_constraint(
        "uq_graph_facts_logical_key_hash", "graph_facts", ["logical_key_hash"]
    )
    op.create_table(
        "graph_extraction_states",
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("extractor_version", sa.String(128), nullable=False),
        sa.Column("vocabulary_version", sa.String(128), nullable=False),
        sa.Column("fact_count", sa.Integer(), nullable=False),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("fact_count >= 0", name="ck_graph_extraction_states_fact_count"),
        sa.ForeignKeyConstraint(["revision_id"], ["document_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "revision_id",
            "extractor_version",
            "vocabulary_version",
            name="pk_graph_extraction_states",
        ),
    )


def downgrade() -> None:
    op.drop_table("graph_extraction_states")
    op.drop_constraint("uq_graph_facts_logical_key_hash", "graph_facts", type_="unique")
    op.drop_column("graph_facts", "logical_key_hash")
    op.drop_column("graph_facts", "provenance_key")
