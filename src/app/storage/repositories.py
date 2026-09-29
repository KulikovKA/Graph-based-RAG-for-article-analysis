"""Настройка движка БД и сессий для API и фоновых обработчиков."""

from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.storage.models import (
    AnalysisJob,
    AnalysisRun,
    Conversation,
    Idea,
    IdeaVersion,
    Message,
    RunEvidence,
    utcnow,
)


def make_engine(database_url: str, *, pool_pre_ping: bool = True) -> Engine:
    """Создать движок SQLAlchemy, приводя адрес PostgreSQL к формату psycopg 3."""
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(database_url, pool_pre_ping=pool_pre_ping)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Вернуть фабрику синхронных сессий без сброса объектов после commit."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class RepositoryConflict(Exception):
    """Запрос несовместим с текущим состоянием в БД."""


class IdempotencyConflict(RepositoryConflict):
    pass


class VersionConflict(RepositoryConflict):
    pass


class ActiveRunConflict(RepositoryConflict):
    pass


class OwnedRepository:
    """Операции с проверкой владельца в транзакции вызывающего кода.

    Вызывающий код фиксирует сессию. Блокировка диалога упорядочивает приём
    запросов и обновление идеи, включая создание первой версии.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def conversation(self, owner_id: UUID, conversation_id: UUID) -> Conversation | None:
        return self.session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.owner_user_id == owner_id,
            )
        )

    def get_run(self, run_id: UUID, *, owner_id: UUID) -> AnalysisRun | None:
        return self.session.scalar(
            select(AnalysisRun).where(
                AnalysisRun.id == run_id, AnalysisRun.owner_user_id == owner_id
            )
        )

    def get_message(self, message_id: UUID, *, owner_id: UUID) -> Message | None:
        return self.session.scalar(
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Message.id == message_id, Conversation.owner_user_id == owner_id)
        )

    def evidence(self, run_id: UUID, *, owner_id: UUID) -> list[RunEvidence]:
        return list(
            self.session.scalars(
                select(RunEvidence)
                .join(AnalysisRun, RunEvidence.run_id == AnalysisRun.id)
                .where(RunEvidence.run_id == run_id, AnalysisRun.owner_user_id == owner_id)
            )
        )

    def accept_run(
        self,
        *,
        owner_id: UUID,
        conversation_id: UUID,
        idempotency_key: str,
        request_hash: str,
        expected_idea_version: int,
        content: str,
        query: str,
        source_run_id: UUID | None = None,
        config_versions: dict[str, Any] | None = None,
    ) -> tuple[AnalysisRun, bool]:
        conversation = self.session.scalar(
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.owner_user_id == owner_id,
            )
            .with_for_update()
        )
        if conversation is None:
            raise LookupError("conversation not found")
        existing = self.session.scalar(
            select(AnalysisRun).where(
                AnalysisRun.owner_user_id == owner_id,
                AnalysisRun.conversation_id == conversation_id,
                AnalysisRun.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_hash != request_hash:
                raise IdempotencyConflict("idempotency key reused with different request")
            return existing, False
        if (
            self.session.scalar(
                select(AnalysisRun.id).where(
                    AnalysisRun.conversation_id == conversation_id,
                    AnalysisRun.status.in_(("pending", "running")),
                )
            )
            is not None
        ):
            raise ActiveRunConflict("conversation already has an active run")
        idea = self.session.scalar(select(Idea).where(Idea.conversation_id == conversation_id))
        base_id = idea.current_version_id if idea else None
        current = self.session.get(IdeaVersion, base_id) if base_id else None
        if (current.version_no if current else 0) != expected_idea_version:
            raise VersionConflict("idea version changed")
        if source_run_id is not None:
            source = self.get_run(source_run_id, owner_id=owner_id)
            if (
                source is None
                or source.conversation_id != conversation_id
                or source.status != "completed"
            ):
                raise LookupError("source run not found")
        message = Message(conversation_id=conversation_id, role="user", content=content)
        self.session.add(message)
        self.session.flush()
        run = AnalysisRun(
            conversation_id=conversation_id,
            owner_user_id=owner_id,
            message_id=message.id,
            source_run_id=source_run_id,
            base_idea_version_id=base_id,
            expected_idea_version=expected_idea_version,
            status="pending",
            stage="accepted",
            query=query,
            coverage_json={},
            config_versions_json=config_versions or {},
            event_seq_high_water=0,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        self.session.add(run)
        self.session.flush()
        message.run_id = run.id
        self.session.add(AnalysisJob(run_id=run.id))
        self.session.flush()
        return run, True

    def apply_idea_version(
        self,
        *,
        owner_id: UUID,
        run_id: UUID,
        normalized: dict[str, Any],
        state_hash: str,
    ) -> IdeaVersion:
        run = self.get_run(run_id, owner_id=owner_id)
        if run is None:
            raise LookupError("run not found")
        conversation = self.session.scalar(
            select(Conversation)
            .where(Conversation.id == run.conversation_id, Conversation.owner_user_id == owner_id)
            .with_for_update()
        )
        if conversation is None:
            raise LookupError("conversation not found")
        self.session.refresh(run)
        if run.planner_applied_at is not None:
            if run.idea_version_id is None:
                raise VersionConflict("planner applied without idea version")
            version = self.session.get(IdeaVersion, run.idea_version_id)
            assert version is not None
            return version
        if run.status not in ("pending", "running") or run.cancel_requested_at is not None:
            raise VersionConflict("run is no longer active")
        idea = self.session.scalar(select(Idea).where(Idea.conversation_id == run.conversation_id))
        if idea is None:
            idea = Idea(conversation_id=run.conversation_id)
            self.session.add(idea)
            self.session.flush()
        current = (
            self.session.get(IdeaVersion, idea.current_version_id)
            if idea.current_version_id
            else None
        )
        if (
            idea.current_version_id != run.base_idea_version_id
            or (current.version_no if current else 0) != run.expected_idea_version
        ):
            raise VersionConflict("idea version changed")
        if current is not None and current.state_hash == state_hash:
            version = current
        else:
            version = IdeaVersion(
                idea_id=idea.id,
                conversation_id=run.conversation_id,
                version_no=run.expected_idea_version + 1,
                parent_version_id=idea.current_version_id,
                normalized_json=normalized,
                state_hash=state_hash,
                created_by_message_id=run.message_id,
            )
            self.session.add(version)
            self.session.flush()
            idea.current_version_id = version.id
        run.idea_version_id = version.id
        run.planner_applied_at = utcnow()
        self.session.flush()
        return version
