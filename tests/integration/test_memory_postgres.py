"""Проверка PostgreSQL; TEST_DATABASE_URL должен указывать на тестовую базу."""

import os
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session
from tests.integration import test_repositories

from app.services.conversations import ConversationService
from app.services.memory import MemoryService
from app.storage.models import Conversation, Message, User

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")
engine = test_repositories.engine


def test_restart_summary_ownership_and_stale_session(engine):
    owner, stranger = uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add_all(
            [
                User(id=owner, email_normalized=f"{owner}@example.test"),
                User(id=stranger, email_normalized=f"{stranger}@example.test"),
            ]
        )
        session.flush()
        conversations = ConversationService(session)
        chat = conversations.create(owner).id
        other = conversations.create(owner).id
        first = conversations.append_message(owner, chat, role="user", content="optical sensor").id
        last = conversations.append_message(owner, chat, role="user", content="latest").id
        session.get(Message, last).created_at = session.get(Message, first).created_at + timedelta(
            seconds=1
        )
        foreign = conversations.append_message(owner, other, role="user", content="foreign").id
        conversations.set_summary(owner, chat, {"legacy": True}, first)
    with Session(engine) as stale:
        cached = stale.get(Conversation, chat)
        assert cached is not None and cached.summary_until_message_id == first
        with Session(engine) as fresh, fresh.begin():
            MemoryService(fresh).rebuild_summary(owner, chat, until_message_id=last)
        assert cached.summary_until_message_id == first
        ConversationService(stale).set_summary(owner, chat, {"stale": True}, first)
        stale.commit()
    with Session(engine) as session:
        memory = MemoryService(session)
        context = memory.context(owner, chat, query="optical", recent_limit=1)
        assert [m.id for m in context.recent] == [last]
        assert [m.id for m in context.relevant] == [first]
        assert context.summary_until_message_id == last
        assert context.summary["schema_version"] == 1
        assert context.summary["builder_version"] == "extractive-v1"
        assert memory.context(owner, other, query="absent", recent_limit=0).recent == ()
        with pytest.raises(LookupError):
            memory.context(stranger, chat)
        with pytest.raises(LookupError):
            memory.rebuild_summary(owner, chat, until_message_id=foreign)


def test_concurrent_summaries_never_move_watermark_back(engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    owner = uuid4()
    with Session(engine) as session, session.begin():
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        service = ConversationService(session)
        chat = service.create(owner).id
        first = service.append_message(owner, chat, role="user", content="first").id
        last = service.append_message(owner, chat, role="user", content="last").id
        session.get(Message, last).created_at = session.get(Message, first).created_at + timedelta(
            seconds=1
        )
    barrier = Barrier(2)

    def update(checkpoint):
        with Session(engine) as session, session.begin():
            barrier.wait(timeout=10)
            ConversationService(session).set_summary(
                owner, chat, {"checkpoint": str(checkpoint)}, checkpoint
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(update, checkpoint) for checkpoint in (first, last)]
        for future in futures:
            future.result(timeout=20)
    with Session(engine) as session:
        summary, checkpoint = ConversationService(session).summary(owner, chat)
        assert checkpoint == last
        assert summary == {"checkpoint": str(last)}
