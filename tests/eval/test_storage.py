"""Транзакции eval_* на SQLite; PostgreSQL schema уже покрыта DB integration."""

import asyncio
import json
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.storage.models import EvalCase, EvalResult, EvalRun
from eval.harness import frozen_inputs
from eval.run import execute, persist
from tests.eval.test_harness import args


@compiles(JSONB, "sqlite")
def compile_jsonb(_type, _compiler, **_kwargs):
    return "JSON"


def test_eval_storage_atomic_rollback_and_reuse(tmp_path):
    output = tmp_path / "run"
    asyncio.run(execute(args(output)))
    run = json.loads((output / "run.json").read_text(encoding="utf-8"))
    _, cases, _ = frozen_inputs()
    url = "sqlite:///" + str(tmp_path / "eval.db")
    engine = create_engine(url)
    for table in (EvalCase.__table__, EvalRun.__table__, EvalResult.__table__):
        table.create(engine)
    persist(url, run, cases)
    run["run_id"] = str(uuid4())
    persist(url, run, cases)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EvalCase)) == 10
        assert session.scalar(select(func.count()).select_from(EvalRun)) == 2
        assert session.scalar(select(func.count()).select_from(EvalResult)) == 20
    changed = json.loads(json.dumps(cases))
    changed[-1]["expected"]["coverage"] = "changed"
    run["run_id"] = str(uuid4())
    with pytest.raises(ValueError, match="DATABASE_CASE_DRIFT"):
        persist(url, run, changed)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EvalRun)) == 2
        assert session.scalar(select(func.count()).select_from(EvalResult)) == 20
    engine.dispose()
