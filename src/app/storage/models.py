"""Схема SQLAlchemy для постоянного состояния приложения.

Межстрочные инварианты по возможности заданы ограничениями PostgreSQL. Начальная
миграция фиксирует эту схему; последующие изменения оформляются миграциями Alembic.
"""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email_normalized IS NOT NULL OR auth_subject IS NOT NULL", name="ck_users_identity"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email_normalized: Mapped[str | None] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(512))
    auth_subject: Mapped[str | None] = mapped_column(String(512), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint("length(token_hash) >= 32", name="ck_auth_sessions_token_hash"),
        CheckConstraint("length(csrf_secret_hash) >= 32", name="ck_auth_sessions_csrf_hash"),
        Index("ix_auth_sessions_token_hash", "token_hash", unique=True),
        Index("ix_auth_sessions_user_expires", "user_id", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    csrf_secret_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("id", "owner_user_id", name="uq_conversations_id_owner"),
        ForeignKeyConstraint(
            ["summary_until_message_id", "id"],
            ["messages.id", "messages.conversation_id"],
            name="fk_conversations_summary_message",
            use_alter=True,
            initially="DEFERRED",
            deferrable=True,
        ),
        Index("ix_conversations_owner_updated", "owner_user_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(512))
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    summary_until_message_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
        CheckConstraint("octet_length(content) <= 8192", name="ck_messages_content_size"),
        UniqueConstraint("id", "conversation_id", name="uq_messages_id_conversation"),
        ForeignKeyConstraint(
            ["run_id", "conversation_id"],
            ["analysis_runs.id", "analysis_runs.conversation_id"],
            name="fk_messages_run_conversation",
            use_alter=True,
            initially="DEFERRED",
            deferrable=True,
        ),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    run_id: Mapped[UUID | None] = mapped_column(Uuid)


class Idea(Base):
    __tablename__ = "ideas"
    __table_args__ = (
        UniqueConstraint("id", "conversation_id", name="uq_ideas_id_conversation"),
        ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["id", "current_version_id"],
            ["idea_versions.idea_id", "idea_versions.id"],
            name="fk_ideas_current_version_same_idea",
            use_alter=True,
            initially="DEFERRED",
            deferrable=True,
            ondelete="CASCADE",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    current_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdeaVersion(Base):
    __tablename__ = "idea_versions"
    __table_args__ = (
        UniqueConstraint("idea_id", "version_no", name="uq_idea_versions_idea_version"),
        UniqueConstraint("idea_id", "id", name="uq_idea_versions_idea_id"),
        UniqueConstraint("id", "conversation_id", name="uq_idea_versions_id_conversation"),
        ForeignKeyConstraint(
            ["idea_id", "conversation_id"],
            ["ideas.id", "ideas.conversation_id"],
            ondelete="CASCADE",
            name="fk_idea_versions_idea_conversation",
        ),
        ForeignKeyConstraint(
            ["idea_id", "parent_version_id"],
            ["idea_versions.idea_id", "idea_versions.id"],
            ondelete="CASCADE",
            name="fk_idea_versions_parent_same_idea",
        ),
        ForeignKeyConstraint(
            ["created_by_message_id", "conversation_id"],
            ["messages.id", "messages.conversation_id"],
            ondelete="CASCADE",
            name="fk_idea_versions_created_message_conversation",
        ),
        CheckConstraint("version_no > 0", name="ck_idea_versions_version_no"),
        Index("ix_idea_versions_idea_version", "idea_id", "version_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    idea_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    normalized_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_message_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        UniqueConstraint("id", "conversation_id", name="uq_analysis_runs_id_conversation"),
        ForeignKeyConstraint(
            ["conversation_id", "owner_user_id"],
            ["conversations.id", "conversations.owner_user_id"],
            ondelete="CASCADE",
            name="fk_runs_owner_conversation",
        ),
        ForeignKeyConstraint(
            ["message_id", "conversation_id"],
            ["messages.id", "messages.conversation_id"],
            ondelete="CASCADE",
            name="fk_runs_message_conversation",
        ),
        ForeignKeyConstraint(
            ["source_run_id", "conversation_id"],
            ["analysis_runs.id", "analysis_runs.conversation_id"],
            ondelete="CASCADE",
            name="fk_runs_source_same_conversation",
        ),
        ForeignKeyConstraint(
            ["base_idea_version_id", "conversation_id"],
            ["idea_versions.id", "idea_versions.conversation_id"],
            ondelete="CASCADE",
            name="fk_runs_base_version_conversation",
        ),
        ForeignKeyConstraint(
            ["idea_version_id", "conversation_id"],
            ["idea_versions.id", "idea_versions.conversation_id"],
            ondelete="CASCADE",
            name="fk_runs_idea_version_conversation",
        ),
        CheckConstraint("expected_idea_version >= 0", name="ck_runs_expected_idea_version"),
        CheckConstraint(
            "status IN ('pending','running','completed','failed','cancelled')",
            name="ck_runs_status",
        ),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ("
            "'analysis','safe_fallback','no_evidence','clarification')",
            name="ck_runs_outcome",
        ),
        CheckConstraint(
            "(status = 'completed' AND outcome IS NOT NULL) OR "
            "(status <> 'completed' AND outcome IS NULL)",
            name="ck_runs_completed_outcome",
        ),
        CheckConstraint(
            "status = 'completed' OR answer_json IS NULL", name="ck_runs_answer_terminal"
        ),
        CheckConstraint(
            "length(idempotency_key) BETWEEN 1 AND 255", name="ck_runs_idempotency_key"
        ),
        UniqueConstraint(
            "owner_user_id",
            "conversation_id",
            "idempotency_key",
            name="uq_runs_owner_conversation_idempotency",
        ),
        Index(
            "uq_analysis_runs_one_active_per_conversation",
            "conversation_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
        Index("ix_analysis_runs_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    message_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_run_id: Mapped[UUID | None] = mapped_column(Uuid)
    base_idea_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    expected_idea_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idea_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    planner_applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    stage: Mapped[str] = mapped_column(String(64), nullable=False, default="accepted")
    outcome: Mapped[str | None] = mapped_column(String(32))
    query: Mapped[str] = mapped_column(Text, nullable=False)
    index_generation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("index_generations.id", ondelete="SET NULL")
    )
    evidence_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    answer_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    coverage_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    event_seq_high_water: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    config_versions_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(128))


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="ck_analysis_jobs_attempts"),
        CheckConstraint(
            "(lease_owner IS NULL) = (lease_until IS NULL)", name="ck_analysis_jobs_lease_pair"
        ),
        Index("ix_analysis_jobs_next_lease", "next_attempt_at", "lease_until"),
    )

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), primary_key=True
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_token: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (
        CheckConstraint("sequence_no > 0", name="ck_run_events_sequence"),
        ForeignKeyConstraint(["run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        Index(
            "uq_run_events_one_terminal",
            "run_id",
            unique=True,
            postgresql_where=text("is_terminal"),
        ),
    )

    run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    sequence_no: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SourceDocument(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_documents_source_external"),
        ForeignKeyConstraint(
            ["id", "active_revision_id"],
            ["document_revisions.document_id", "document_revisions.id"],
            name="fk_source_documents_active_revision_same_document",
            use_alter=True,
            initially="DEFERRED",
            deferrable=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date)
    active_revision_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentRevision(Base):
    __tablename__ = "document_revisions"
    __table_args__ = (
        UniqueConstraint("id", "document_id", name="uq_document_revisions_id_document"),
        UniqueConstraint("document_id", "content_hash", name="uq_document_revisions_document_hash"),
        CheckConstraint(
            "ingest_state IN ('discovered','normalized','indexed','failed')",
            name="ck_document_revisions_ingest_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ingest_state: Mapped[str] = mapped_column(String(24), nullable=False, default="discovered")
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunks"
    __table_args__ = (
        UniqueConstraint("id", "revision_id", name="uq_evidence_chunks_id_revision"),
        UniqueConstraint(
            "revision_id",
            "section",
            "ordinal",
            "hash",
            name="uq_chunks_revision_section_ordinal_hash",
        ),
        CheckConstraint(
            "ordinal >= 0 AND section_start >= 0 AND section_end >= section_start",
            name="ck_evidence_chunks_offsets",
        ),
        Index("ix_evidence_chunks_revision_section", "revision_id", "section"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    section: Mapped[str] = mapped_column(String(256), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    section_start: Mapped[int] = mapped_column(Integer, nullable=False)
    section_end: Mapped[int] = mapped_column(Integer, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)


class RunEvidence(Base):
    __tablename__ = "run_evidence"
    __table_args__ = (
        ForeignKeyConstraint(["run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["revision_id", "document_id"],
            ["document_revisions.id", "document_revisions.document_id"],
            name="fk_run_evidence_revision_document",
        ),
        ForeignKeyConstraint(
            ["chunk_id", "revision_id"],
            ["evidence_chunks.id", "evidence_chunks.revision_id"],
            name="fk_run_evidence_chunk_revision",
        ),
        CheckConstraint("span_start >= 0 AND span_end >= span_start", name="ck_run_evidence_span"),
        Index("ix_run_evidence_document", "run_id", "document_id"),
    )

    run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    evidence_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    chunk_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    span_start: Mapped[int] = mapped_column(Integer, nullable=False)
    span_end: Mapped[int] = mapped_column(Integer, nullable=False)
    quoted_span: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_score: Mapped[float | None]
    rerank_score: Mapped[float | None]
    index_generation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("index_generations.id", ondelete="SET NULL")
    )


class GraphFact(Base):
    __tablename__ = "graph_facts"
    __table_args__ = (
        ForeignKeyConstraint(["revision_id"], ["document_revisions.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["chunk_id", "revision_id"],
            ["evidence_chunks.id", "evidence_chunks.revision_id"],
            name="fk_graph_facts_chunk_revision",
        ),
        CheckConstraint(
            "(span_start IS NULL AND span_end IS NULL) OR "
            "(span_start >= 0 AND span_end >= span_start)",
            name="ck_graph_facts_span",
        ),
        CheckConstraint(
            "provenance_kind IN ('source_text','abstract','metadata','synthetic')",
            name="ck_graph_facts_provenance",
        ),
        Index("ix_graph_facts_revision", "revision_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    from_key: Mapped[str] = mapped_column(String(512), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(128), nullable=False)
    to_key: Mapped[str] = mapped_column(String(512), nullable=False)
    chunk_id: Mapped[UUID | None] = mapped_column(Uuid)
    span_start: Mapped[int | None] = mapped_column(Integer)
    span_end: Mapped[int | None] = mapped_column(Integer)
    metadata_pointer: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    provenance_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(128), nullable=False)
    vocabulary_version: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float | None]
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RevisionIndexAck(Base):
    __tablename__ = "revision_index_acks"
    __table_args__ = (
        ForeignKeyConstraint(["revision_id"], ["document_revisions.id"], ondelete="CASCADE"),
        CheckConstraint(
            "backend IN ('qdrant','domain_graph','lightrag_context')",
            name="ck_revision_index_acks_backend",
        ),
        UniqueConstraint(
            "revision_id",
            "backend",
            "indexer_version",
            "projection_version",
            name="uq_revision_index_acks_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    backend: Mapped[str] = mapped_column(String(32), nullable=False)
    indexer_version: Mapped[str] = mapped_column(String(128), nullable=False)
    projection_version: Mapped[str] = mapped_column(String(128), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class IndexGeneration(Base):
    __tablename__ = "index_generations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("index_generations.id", ondelete="SET NULL")
    )
    config_versions_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IndexCatalog(Base):
    __tablename__ = "index_catalog"
    __table_args__ = (CheckConstraint("id = 1", name="ck_index_catalog_singleton"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    current_generation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("index_generations.id", ondelete="RESTRICT")
    )


class IndexMember(Base):
    __tablename__ = "index_members"
    __table_args__ = (
        ForeignKeyConstraint(
            ["revision_id", "document_id"],
            ["document_revisions.id", "document_revisions.document_id"],
            name="fk_index_members_revision_document",
        ),
        UniqueConstraint(
            "generation_id", "revision_id", name="uq_index_members_generation_revision"
        ),
        Index("ix_index_members_generation_revision", "generation_id", "revision_id"),
    )

    generation_id: Mapped[UUID] = mapped_column(
        ForeignKey("index_generations.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','running','completed','failed')", name="ck_ingestion_jobs_status"
        ),
        CheckConstraint("attempts >= 0", name="ck_ingestion_jobs_attempts"),
        UniqueConstraint(
            "source", "external_id", "payload_hash", name="uq_ingestion_jobs_idempotency"
        ),
        Index("ix_ingestion_jobs_lease", "status", "lease_until", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lease_token: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index(
            "ix_outbox_events_unprocessed",
            "created_at",
            postgresql_where=text("processed_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutboxAck(Base):
    """Постоянное подтверждение события outbox отдельным потребителем."""

    __tablename__ = "outbox_acks"

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("outbox_events.id", ondelete="CASCADE"), primary_key=True
    )
    consumer: Mapped[str] = mapped_column(String(128), primary_key=True)
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EvalCase(Base):
    __tablename__ = "eval_cases"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    split: Mapped[str] = mapped_column(String(16), nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expected_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    config_versions_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    snapshot_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvalResult(Base):
    __tablename__ = "eval_results"
    __table_args__ = (
        UniqueConstraint("eval_run_id", "eval_case_id", name="uq_eval_results_run_case"),
        ForeignKeyConstraint(["eval_run_id"], ["eval_runs.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["eval_case_id"], ["eval_cases.id"], ondelete="RESTRICT"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    eval_run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    eval_case_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
