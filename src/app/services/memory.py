"""Ограниченный контекст и воспроизводимая сводка истории чата."""

import copy
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.services.conversations import ConversationService
from app.storage.models import IdeaVersion, Message, RunEvidence


@dataclass(frozen=True)
class MemoryContext:
    recent: tuple[Message, ...]
    relevant: tuple[Message, ...]
    summary: dict[str, Any] | None
    summary_until_message_id: UUID | None
    idea_version: IdeaVersion | None


@dataclass(frozen=True)
class HistoricalMemory:
    snapshot: dict[str, Any]
    idea_version: IdeaVersion | None
    generation_id: UUID | None
    evidence: tuple[RunEvidence, ...]


class MemoryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.conversations = ConversationService(session)

    def context(
        self,
        owner_id: UUID,
        conversation_id: UUID,
        *,
        query: str = "",
        idea_version_id: UUID | None = None,
        recent_limit: int = 10,
        relevant_limit: int = 5,
    ) -> MemoryContext:
        if not 0 <= recent_limit <= 50 or not 0 <= relevant_limit <= 50:
            raise ValueError("context limits must be between 0 and 50")
        self.conversations.get(owner_id, conversation_id)
        version = self.conversations.current_idea(owner_id, conversation_id)
        if idea_version_id is not None:
            version = self.session.scalar(
                select(IdeaVersion).where(
                    IdeaVersion.id == idea_version_id,
                    IdeaVersion.conversation_id == conversation_id,
                )
            )
            if version is None:
                raise LookupError("idea version not found")
        # Ограниченный пул не создаёт неограниченную нагрузку на длинных чатах.
        pool = list(
            self.session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(500)
            )
        )
        recent = list(reversed(pool[:recent_limit]))
        recent_ids = {message.id for message in recent}
        terms = set(re.findall(r"\w+", query.casefold()))
        ranked = []
        for index, message in enumerate(pool):
            if message.id in recent_ids:
                continue
            score = len(terms & set(re.findall(r"\w+", message.content.casefold())))
            if score:
                ranked.append((-score, index, message))
        ranked.sort(key=lambda item: (item[0], item[1]))
        summary, checkpoint = self.conversations.summary(owner_id, conversation_id)
        return MemoryContext(
            tuple(recent),
            tuple(item[2] for item in ranked[:relevant_limit]),
            summary,
            checkpoint,
            version,
        )

    def historical(
        self, owner_id: UUID, conversation_id: UUID, source_run_id: UUID
    ) -> HistoricalMemory:
        self.conversations.get(owner_id, conversation_id)
        run = self.conversations.repository.get_run(source_run_id, owner_id=owner_id)
        if (
            run is None
            or run.conversation_id != conversation_id
            or run.status != "completed"
            or run.evidence_snapshot_json is None
        ):
            raise LookupError("source run not found")
        version = None
        if run.idea_version_id is not None:
            version = self.session.scalar(
                select(IdeaVersion).where(
                    IdeaVersion.id == run.idea_version_id,
                    IdeaVersion.conversation_id == conversation_id,
                )
            )
            if version is None:
                raise LookupError("idea version not found")
        return HistoricalMemory(
            copy.deepcopy(run.evidence_snapshot_json),
            version,
            run.index_generation_id,
            tuple(self.conversations.repository.evidence(source_run_id, owner_id=owner_id)),
        )

    def rebuild_summary(
        self, owner_id: UUID, conversation_id: UUID, *, until_message_id: UUID
    ) -> None:
        self.conversations.get(owner_id, conversation_id)
        checkpoint = self.session.scalar(
            select(Message).where(
                Message.id == until_message_id, Message.conversation_id == conversation_id
            )
        )
        if checkpoint is None:
            raise LookupError("summary checkpoint not found")
        history = list(
            self.session.scalars(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    or_(
                        Message.created_at < checkpoint.created_at,
                        and_(
                            Message.created_at == checkpoint.created_at, Message.id <= checkpoint.id
                        ),
                    ),
                )
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(20)
            )
        )
        summary = {
            "schema_version": 1,
            "builder_version": "extractive-v1",
            "messages": [
                {"id": str(item.id), "role": item.role, "excerpt": item.content[:256]}
                for item in reversed(history)
            ],
        }
        self.conversations.set_summary(owner_id, conversation_id, summary, until_message_id)
