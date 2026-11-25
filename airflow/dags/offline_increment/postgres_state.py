"""Изолированный PostgreSQL-прототип барьера страниц; не подключён к DAG."""

import json
from dataclasses import asdict

from sqlalchemy import Engine, text

from .pipeline import Interval, Item, Page, Progress, Source, cursor_hash


class StateConflict(Exception):
    """Несовпадение закреплённых входов или предпосылок публикации."""


class PostgresPageState:
    """Таблицы создаёт вызывающая сторона в отдельной схеме, не миграция приложения."""

    def __init__(self, engine: Engine, config_version: str, versions: dict[str, str]):
        if (
            not config_version
            or set(versions) != {"domain_graph", "qdrant", "qa"}
            or not all(versions.values())
        ):
            raise ValueError("config_version")
        self.engine, self.config_version = engine, config_version
        self.versions = dict(versions)

    def initialize(self) -> None:
        with self.engine.begin() as c:
            c.execute(
                text("""CREATE TABLE IF NOT EXISTS offline_state (
                source text NOT NULL, starts timestamptz NOT NULL, ends timestamptz NOT NULL,
                config text NOT NULL, state jsonb NOT NULL,
                PRIMARY KEY (source, starts, ends))""")
            )
            c.execute(
                text("""CREATE TABLE IF NOT EXISTS offline_catalog (
                id integer PRIMARY KEY CHECK (id = 1), generation text)""")
            )
            c.execute(text("INSERT INTO offline_catalog VALUES (1, NULL) ON CONFLICT DO NOTHING"))

    def _locked(self, c, source: Source, interval: Interval):
        params = {"source": source, "starts": interval.start, "ends": interval.end}
        initial = {"cursor": None, "completed": False, "history": [], "pages": {}}
        c.execute(
            text("""INSERT INTO offline_state VALUES
            (:source, :starts, :ends, :config, CAST(:state AS jsonb))
            ON CONFLICT DO NOTHING"""),
            {**params, "config": self.config_version, "state": json.dumps(initial)},
        )
        row = c.execute(
            text("""SELECT config, state FROM offline_state WHERE source=:source
            AND starts=:starts AND ends=:ends FOR UPDATE"""),
            params,
        ).one()
        if row.config != self.config_version:
            raise StateConflict("config")
        return params, row.state

    @staticmethod
    def _save(c, params, state):
        c.execute(
            text("""UPDATE offline_state SET state=CAST(:state AS jsonb)
            WHERE source=:source AND starts=:starts AND ends=:ends"""),
            {**params, "state": json.dumps(state, ensure_ascii=False)},
        )

    def progress(self, source: Source, interval: Interval) -> Progress:
        with self.engine.begin() as c:
            _, state = self._locked(c, source, interval)
            return Progress(state["cursor"], state["completed"], tuple(state["history"]))

    def freeze(
        self,
        source: Source,
        interval: Interval,
        cursor: str | None,
        page: Page,
        revisions: dict[str, str],
        generation: str | None,
    ) -> None:
        """Закрепить страницу и отображение revision key → идентификатор ревизии."""
        frozen = {
            "page": asdict(page),
            "revisions": revisions,
            "acks": {},
            "qa": {},
            "committed": None,
            "versions": self.versions,
            "generation": generation,
        }
        # JSON нормализует tuple в list для последующего точного сравнения.
        frozen = json.loads(json.dumps(frozen, ensure_ascii=False))
        key = cursor_hash(cursor)
        with self.engine.begin() as c:
            params, state = self._locked(c, source, interval)
            old = state["pages"].get(key)
            if old is not None:
                if (
                    old["page"] != frozen["page"]
                    or old["revisions"] != revisions
                    or old["versions"] != self.versions
                    or old["generation"] != generation
                ):
                    raise StateConflict("frozen_page")
                return
            if state["completed"] or state["cursor"] != cursor:
                raise StateConflict("checkpoint")
            item_keys = [
                json.dumps(
                    [i.external_id, i.revision_key], ensure_ascii=False, separators=(",", ":")
                )
                for i in page.items
            ]
            if (
                len(set(item_keys)) != len(item_keys)
                or not set(revisions).issubset(item_keys)
                or len(set(revisions.values())) != len(revisions)
                or any(
                    not isinstance(revision, str) or not revision for revision in revisions.values()
                )
                or (not revisions and generation is not None)
                or (bool(revisions) and (not isinstance(generation, str) or not generation))
            ):
                raise StateConflict("revisions")
            state["pages"][key] = frozen
            self._save(c, params, state)

    def prepared(
        self, source: Source, interval: Interval, cursor: str | None
    ) -> tuple[Page, dict[str, str], str | None] | None:
        with self.engine.begin() as c:
            _, state = self._locked(c, source, interval)
            entry = state["pages"].get(cursor_hash(cursor))
            if entry is None:
                return None
            if entry["versions"] != self.versions:
                raise StateConflict("versions")
            saved = entry["page"]
            page = Page(tuple(Item(**item) for item in saved["items"]), saved["next_cursor"])
            return page, dict(entry["revisions"]), entry["generation"]

    def frozen_page(self, source: Source, interval: Interval, cursor: str | None) -> Page | None:
        prepared = self.prepared(source, interval, cursor)
        return None if prepared is None else prepared[0]

    def receipt(
        self,
        source: Source,
        interval: Interval,
        cursor: str | None,
        revision: str,
        kind: str,
        version: str,
        generation: str,
    ) -> None:
        if kind not in ("domain_graph", "qdrant", "qa") or not version:
            raise StateConflict("receipt")
        with self.engine.begin() as c:
            params, state = self._locked(c, source, interval)
            page = state["pages"].get(cursor_hash(cursor))
            if (
                page is None
                or page["generation"] != generation
                or not generation
                or revision not in page["revisions"].values()
                or page["committed"]
            ):
                raise StateConflict("receipt")
            bucket = page["qa"] if kind == "qa" else page["acks"]
            existing = bucket.setdefault(revision, {})
            generations = existing.setdefault(kind, {})
            versions = generations.setdefault(generation, [])
            if version not in versions:
                versions.append(version)
            self._save(c, params, state)

    def commit(
        self,
        source: Source,
        interval: Interval,
        cursor: str | None,
        page: Page,
        revisions: dict[str, str],
        expected_history: tuple[str, ...],
        expected_generation: str | None,
        generation: str | None,
        versions: dict[str, str],
    ) -> None:
        if (
            (not revisions and generation is not None)
            or (bool(revisions) and (not isinstance(generation, str) or not generation))
            or set(versions) != {"domain_graph", "qdrant", "qa"}
            or not all(versions.values())
            or versions != self.versions
        ):
            raise StateConflict("versions")
        with self.engine.begin() as c:
            params, state = self._locked(c, source, interval)
            entry = state["pages"].get(cursor_hash(cursor))
            requested = {
                "generation": generation,
                "previous": expected_generation,
                "history": list(expected_history),
                "versions": versions,
            }
            encoded_page = json.loads(json.dumps(asdict(page), ensure_ascii=False))
            if (
                entry is None
                or entry["page"] != encoded_page
                or entry["revisions"] != revisions
                or entry["versions"] != self.versions
                or entry["generation"] != generation
            ):
                raise StateConflict("frozen_page")
            if entry["committed"] is not None:
                if entry["committed"] != requested:
                    raise StateConflict("replay")
                return
            if (
                state["completed"]
                or state["cursor"] != cursor
                or state["history"] != list(expected_history)
            ):
                raise StateConflict("checkpoint")
            digest = cursor_hash(cursor)
            if digest in expected_history or (
                page.next_cursor is not None
                and cursor_hash(page.next_cursor) in (*expected_history, digest)
            ):
                raise StateConflict("cursor")
            for revision in revisions.values():
                if any(
                    versions[k]
                    not in entry["acks"].get(revision, {}).get(k, {}).get(generation, [])
                    for k in ("domain_graph", "qdrant")
                ) or versions["qa"] not in entry["qa"].get(revision, {}).get("qa", {}).get(
                    generation, []
                ):
                    raise StateConflict("receipts")
            current = c.execute(
                text("SELECT generation FROM offline_catalog WHERE id=1 FOR UPDATE")
            ).scalar_one()
            if current != expected_generation:
                raise StateConflict("generation")
            if revisions:
                c.execute(
                    text("UPDATE offline_catalog SET generation=:generation WHERE id=1"),
                    {"generation": generation},
                )
            entry["committed"] = requested
            state.update(
                cursor=page.next_cursor,
                completed=page.next_cursor is None,
                history=[*expected_history, digest],
            )
            self._save(c, params, state)
