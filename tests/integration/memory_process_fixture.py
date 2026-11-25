import asyncio
import json
import logging
import os
import sys

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.auth import AuthSettings
from app.domain.contracts import CoverageV1
from app.domain.evidence import RetrievalResult
from app.domain.planner import PlannerResult, PlannerV1
from app.main import create_app
from app.services.analysis_run import AnalysisRunService
from app.services.analyst import Analyst
from app.services.auth import AuthService
from app.services.memory_cache import build_stage_cache
from app.services.retrieval import CandidateRetrievalService, RetrievalConfig, build_retrieval_query
from app.storage.models import AnalysisRun, EvidenceChunk
from app.storage.repositories import make_engine
from app.workers.analysis import AnalysisWorker

ORIGIN = "https://memory-process.example.test"


class Planner:
    model_id = "fixture"

    async def plan(self, *, context, **kwargs):
        with open(os.environ["FIXTURE_TRACE"], "a", encoding="utf-8") as trace:
            trace.write(json.dumps({"summary": kwargs.get("summary", "")}) + "\n")
        intent = (
            "explain_evidence"
            if context.source_run_id
            else ("new_idea" if context.idea is None else "general_followup")
        )
        plan = PlannerV1(
            schema_version=1,
            intent=intent,
            base_idea_version=context.version,
            add_features=[{"text": "optical sensor", "rationale": "fixture"}]
            if intent == "new_idea"
            else [],
            remove_feature_ids=[],
            replace_features=[],
            focus_evidence_ids=list(context.allowed_evidence_ids)
            if intent == "explain_evidence"
            else [],
            suggested_retrieval=True,
            confidence=1.0,
        )
        return PlannerResult(plan, 1)


class Retrieval(CandidateRetrievalService):
    def __init__(self, sessions):
        self.session_factory = sessions
        self.config = RetrievalConfig()

    async def search(self, *, original_query, idea, generation_id, request_id):
        with self.session_factory() as session:
            ids = set(session.scalars(select(EvidenceChunk.id)))
        candidates = self._load_candidates_by_chunk_ids(ids, generation_id, "metadata")
        return RetrievalResult(
            generation_id,
            build_retrieval_query(original_query, idea),
            candidates,
            CoverageV1(sources=[], channels=[], partial=False, historical=False),
        )


class SyntheticAnalyst(Analyst):
    async def analyze(self, *, idea, pack, coverage, **kwargs):
        return self._fallback(idea, pack, coverage, 1, ("FIXTURE",))


def main():
    logging.basicConfig(level=logging.INFO)
    engine = make_engine(os.environ["FIXTURE_DATABASE_URL"])
    sessions = sessionmaker(engine, class_=Session, expire_on_commit=False)
    role = sys.argv[1]
    payload = json.loads(sys.argv[2])
    if role == "api":
        app = create_app(
            auth=AuthService(sessions),
            auth_settings=AuthSettings(origins=(ORIGIN,)),
            stage_cache=build_stage_cache(
                os.environ["TEST_REDIS_URL"], os.environ["FIXTURE_SECRET"]
            ),
        )
        with TestClient(app, base_url=ORIGIN) as client:
            login = client.post(
                "/api/v1/auth/login",
                headers={"Origin": ORIGIN},
                json={"email": payload["email"], "password": payload["password"]},
            )
            assert login.status_code == 200, login.text
            client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": login.json()["csrf_token"]})
            response = client.request(
                payload["method"],
                payload["path"],
                json=payload.get("body"),
                headers=payload.get("headers", {}),
            )
            print(
                json.dumps(
                    {"pid": os.getpid(), "status": response.status_code, "body": response.json()}
                )
            )
    else:

        async def score(query, documents, request_id, timeout, cancel):
            return [0.75] * len(documents)

        service = AnalysisRunService(
            sessions,
            Planner(),
            Retrieval(sessions),
            SyntheticAnalyst(object(), model_id="fixture", prompt="{schema_json}{input_json}"),
            rerank=score,
            token_counter=lambda _: 1,
            retrieval_config_hash="a" * 64,
            analyst_tokenizer_version="fixture-v1",
            stage_cache=build_stage_cache(
                os.environ["TEST_REDIS_URL"], os.environ["FIXTURE_SECRET"]
            ),
        )
        execute = service.execute

        async def traced_execute(*args, **kwargs):
            try:
                return await execute(*args, **kwargs)
            except Exception:
                import traceback

                traceback.print_exc()
                raise

        service.execute = traced_execute
        processed = asyncio.run(AnalysisWorker(sessions, service).run_once())
        with sessions() as db:
            rows = [
                (str(run.id), run.status, run.error_code) for run in db.scalars(select(AnalysisRun))
            ]
        print(json.dumps({"pid": os.getpid(), "processed": processed, "runs": rows}))
    engine.dispose()


if __name__ == "__main__":
    main()
