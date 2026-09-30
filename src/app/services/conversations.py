"""Durable, owner-scoped conversation and idea history operations."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models import (
    Conversation,
    Idea,
    IdeaVersion,
    Message,
    RunEvidence,
)
from app.storage.repositories import OwnedRepository


class ConversationService:
    """Conversation reads and writes; PostgreSQL remains the source of truth."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OwnedRepository(session)

    def create(self, owner_id: UUID, *, title: str | None = None) -> Conversation:
        conversation = Conversation(owner_user_id=owner_id, title=title)
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def list_conversations(self, owner_id: UUID, *, limit: int = 50) -> list[Conversation]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return list(
            self.session.scalars(
                select(Conversation)
                .where(Conversation.owner_user_id == owner_id)
                .order_by(Conversation.updated_at.desc(), Conversation.id)
                .limit(limit)
            )
        )

    def get(self, owner_id: UUID, conversation_id: UUID) -> Conversation:
        conversation = self.repository.conversation(owner_id, conversation_id)
        if conversation is None:
            raise LookupError("conversation not found")
        return conversation

    def rename(self, owner_id: UUID, conversation_id: UUID, title: str | None) -> Conversation:
        conversation = self.get(owner_id, conversation_id)
        conversation.title = title
        self.session.flush()
        return conversation

    def delete(self, owner_id: UUID, conversation_id: UUID) -> None:
        conversation = self.get(owner_id, conversation_id)
        self.session.delete(conversation)
        self.session.flush()

    def append_message(
        self, owner_id: UUID, conversation_id: UUID, *, role: str, content: str
    ) -> Message:
        """Append a durable transcript entry; existing messages are never edited."""
        conversation = self.get(owner_id, conversation_id)
        if role not in {"user", "assistant"}:
            raise ValueError("role must be user or assistant")
        if len(content.encode("utf-8")) > 8192:
            raise ValueError("message exceeds 8192 bytes")
        message = Message(conversation_id=conversation.id, role=role, content=content)
        self.session.add(message)
        self.session.flush()
        return message

    def messages(self, owner_id: UUID, conversation_id: UUID, *, limit: int = 100) -> list[Message]:
        self.get(owner_id, conversation_id)
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        return list(
            self.session.scalars(
                select(Message)
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(
                    Message.conversation_id == conversation_id,
                    Conversation.owner_user_id == owner_id,
                )
                .order_by(Message.created_at, Message.id)
                .limit(limit)
            )
        )

    def idea_versions(self, owner_id: UUID, conversation_id: UUID) -> list[IdeaVersion]:
        self.get(owner_id, conversation_id)
        return list(
            self.session.scalars(
                select(IdeaVersion)
                .join(Idea, IdeaVersion.idea_id == Idea.id)
                .where(Idea.conversation_id == conversation_id)
                .order_by(IdeaVersion.version_no)
            )
        )

    def current_idea(self, owner_id: UUID, conversation_id: UUID) -> IdeaVersion | None:
        self.get(owner_id, conversation_id)
        idea = self.session.scalar(select(Idea).where(Idea.conversation_id == conversation_id))
        if idea is None or idea.current_version_id is None:
            return None
        return self.session.get(IdeaVersion, idea.current_version_id)

    def summary(
        self, owner_id: UUID, conversation_id: UUID
    ) -> tuple[dict[str, Any] | None, UUID | None]:
        """Return the explicitly derived summary checkpoint; messages remain authoritative."""
        conversation = self.get(owner_id, conversation_id)
        return conversation.summary_json, conversation.summary_until_message_id

    def set_summary(
        self,
        owner_id: UUID,
        conversation_id: UUID,
        summary: dict[str, Any],
        until_message_id: UUID,
    ) -> None:
        """Store a derived summary only when its checkpoint belongs to this conversation."""
        conversation = self.get(owner_id, conversation_id)
        checkpoint = self.session.scalar(
            select(Message.id).where(
                Message.id == until_message_id,
                Message.conversation_id == conversation_id,
            )
        )
        if checkpoint is None:
            raise LookupError("summary checkpoint not found")
        conversation.summary_json = summary
        conversation.summary_until_message_id = until_message_id
        self.session.flush()

    def historical_evidence(self, owner_id: UUID, source_run_id: UUID) -> list[RunEvidence]:
        """Read evidence from its immutable completed run after checking owner and state."""
        run = self.repository.get_run(source_run_id, owner_id=owner_id)
        if run is None or run.status != "completed":
            raise LookupError("source run not found")
        return self.repository.evidence(source_run_id, owner_id=owner_id)
