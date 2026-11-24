"""Атомарное удаление чата с согласованием блокировок worker и приёма."""

import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from app.storage.models import AnalysisJob, AnalysisRun, Conversation


class ChatBusy(Exception):
    """Конкурирующая транзакция не освободила блокировки за отведённое число попыток."""


def _lock_and_delete(db: Session, owner_id: UUID, conversation_id: UUID) -> None:
    conversation = db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.owner_user_id == owner_id)
        .with_for_update(nowait=True)
    )
    if conversation is None:
        raise LookupError("conversation not found")

    # Worker держит job → run и иногда ждёт conversation. NOWAIT и откат всей
    # транзакции исключают цикл ожидания; блокировка conversation закрывает приём.
    list(
        db.scalars(
            select(AnalysisJob)
            .join(AnalysisRun, AnalysisRun.id == AnalysisJob.run_id)
            .where(AnalysisRun.conversation_id == conversation_id)
            .order_by(AnalysisJob.run_id)
            .with_for_update(of=AnalysisJob, nowait=True)
        )
    )
    list(
        db.scalars(
            select(AnalysisRun)
            .where(AnalysisRun.conversation_id == conversation_id)
            .order_by(AnalysisRun.id)
            .with_for_update(nowait=True)
        )
    )
    db.delete(conversation)
    db.flush()


def delete_conversation(
    sessions: sessionmaker[Session], owner_id: UUID, conversation_id: UUID
) -> None:
    """Удалить чат и его потомков; вернуть управление только после commit."""
    for attempt in range(5):
        try:
            with sessions.begin() as db:
                _lock_and_delete(db, owner_id, conversation_id)
            return
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) != "55P03":
                raise
            if attempt == 4:
                raise ChatBusy("conversation is busy") from None
            time.sleep(0.01 * (attempt + 1))
