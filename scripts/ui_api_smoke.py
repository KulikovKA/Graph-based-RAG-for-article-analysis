"""Временный API + synthetic worker только для browser smoke UI-001.

Запускается с TEST_DATABASE_URL; собственная схема удаляется при штатном завершении.
Не использовать вместо production worker: результат всегда synthetic/no_evidence.
"""

import hashlib
import json
import os
import threading
from datetime import timedelta
from uuid import uuid4

import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.api.auth import AuthSettings
from app.domain.contracts import AnswerV1, LimitationV1, PublicAnalysisV1
from app.domain.planner import IdeaV1
from app.main import create_app
from app.services.analysis_run import ProgressCounts, StageProgress
from app.services.auth import AuthService
from app.services.run_events import append_progress
from app.storage.jobs import JobRepository
from app.storage.models import AnalysisRun, utcnow
from app.storage.repositories import OwnedRepository, make_engine, make_session_factory


def main() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    admin = make_engine(url)
    schema = "ui_smoke_" + uuid4().hex
    with admin.begin() as db:
        db.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = url + ("&" if "?" in url else "?") + f"options=-csearch_path%3D{schema}"
    engine = make_engine(scoped_url)
    stop = threading.Event()
    thread: threading.Thread | None = None
    try:
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", scoped_url.replace("%", "%%"))
        command.upgrade(config, "head")
        service = AuthService(make_session_factory(engine))
        service.create_account("ui-smoke@example.test", "synthetic-smoke-password")

        def worker() -> None:
            while not stop.wait(0.25):
                with service.sessions.begin() as db:
                    lease = JobRepository(db).claim_next(
                        worker="ui-smoke", duration=timedelta(seconds=30)
                    )
                    if lease is None:
                        continue
                    run = db.get(AnalysisRun, lease.run_id)
                    assert run is not None
                    normalized = IdeaV1(features=[], domain=run.query[:200]).model_dump(mode="json")
                    version = OwnedRepository(db).apply_idea_version(
                        owner_id=run.owner_user_id,
                        run_id=run.id,
                        normalized=normalized,
                        state_hash=hashlib.sha256(
                            json.dumps(normalized, sort_keys=True).encode()
                        ).hexdigest(),
                    )
                    append_progress(
                        db,
                        run.id,
                        worker="ui-smoke",
                        token=lease.token,
                        update=StageProgress(
                            attempt=lease.attempt,
                            stage="planning",
                            phase="completed",
                            stage_started_at=utcnow(),
                            counts=ProgressCounts(feature_count=0),
                            idea_version_id=version.id,
                        ),
                    )
                if stop.wait(1):
                    return
                text_value = "Проверка интерфейса завершена. Подтверждений в тестовом корпусе нет."
                limitation = LimitationV1(code="no_evidence", message=text_value)
                answer = AnswerV1(
                    summary=[],
                    matches=[],
                    differences=[],
                    limitations=[limitation],
                    followup_suggestions=[],
                )
                presentation = {
                    "schema_version": 1,
                    "renderer_version": "ui-smoke-v1",
                    "text": text_value,
                    "chunk_count": 1,
                    "text_sha256": hashlib.sha256(text_value.encode()).hexdigest(),
                    "presentation_id": hashlib.sha256(
                        ("ui-smoke-v1" + text_value).encode()
                    ).hexdigest(),
                }
                with service.sessions.begin() as db:
                    JobRepository(db).complete(
                        lease.run_id,
                        worker="ui-smoke",
                        token=lease.token,
                        outcome="no_evidence",
                        answer=answer.model_dump(mode="json"),
                        public_analysis=PublicAnalysisV1(
                            items=[], limitations=[limitation]
                        ).model_dump(mode="json"),
                        answer_presentation=presentation,
                        coverage={
                            "sources": [],
                            "channels": [],
                            "partial": False,
                            "historical": False,
                        },
                    )

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        origin = os.environ.get("UI_SMOKE_ORIGIN", "http://127.0.0.1:5180")
        app = create_app(
            auth=service,
            auth_settings=AuthSettings(
                origins=(origin,), http_dev_enabled=True, cookie_secure=False
            ),
        )
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="warning",
            proxy_headers=True,
            forwarded_allow_ips="*",
        )
    finally:
        stop.set()
        if thread is not None:
            thread.join(timeout=3)
        engine.dispose()
        with admin.begin() as db:
            db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


if __name__ == "__main__":
    main()
