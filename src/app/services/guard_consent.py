"""Долговечное согласие на внешний контекст для отдельного запуска."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.services.guard import Consent, Scope
from app.storage.models import AnalysisRun, ExternalConsent

NOTICE_VERSION = "groq_context_v1"


def owned_run(db: Session, owner: UUID, run_id: UUID, *, lock: bool = False) -> AnalysisRun | None:
    query = select(AnalysisRun).where(AnalysisRun.id == run_id, AnalysisRun.owner_user_id == owner)
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def granted(db: Session, run_id: UUID) -> ExternalConsent | None:
    row = db.get(ExternalConsent, run_id)
    return row if row is not None and row.notice_version == NOTICE_VERSION else None


def grant(db: Session, run_id: UUID) -> None:
    row = db.get(ExternalConsent, run_id)
    if row is None:
        db.add(ExternalConsent(run_id=run_id, notice_version=NOTICE_VERSION, revision=uuid4()))
    elif row.notice_version != NOTICE_VERSION:
        row.notice_version = NOTICE_VERSION
        row.revision = uuid4()


def revoke(db: Session, run_id: UUID) -> None:
    row = db.get(ExternalConsent, run_id)
    if row is not None:
        db.delete(row)


class ConsentAuthority:
    """Только проверка согласия; источники контекста задаются отдельным портом."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    async def check(self, principal: UUID, selected: Scope) -> Consent | None:
        if principal != selected.owner_id:
            return None
        with self.sessions() as db:
            run = owned_run(db, principal, selected.run_id)
            if run is None or run.conversation_id != selected.conversation_id:
                return None
            if (run.index_generation_id or run.id) != selected.snapshot_id:
                return None
            row = granted(db, run.id)
            if row is None:
                return None
            return Consent(selected, row.notice_version, True, row.revision)
