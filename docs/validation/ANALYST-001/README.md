# ANALYST-001 — проверенный Analyst v1

Дата реализации: 2026-09-30. Analyst использует закреплённый `gemma4:26b-a4b-it-mtp-q4_K_M` через `InferenceProvider`; вызов не запускает job/storage publication и сохраняет границу JOB-002.

## Реализовано

- Закрытая схема AnalysisV1 и проверка feature/document/evidence membership, соответствия evidence тому же документу, точных Unicode-срезов по offsets и полного множества unresolved features.
- Одна repair-попытка в общем deadline для invalid JSON/schema/context validation; в repair передаются ограниченный structured draft и коды проверок, без reasoning. Timeout/protocol/backend errors переходят к safe fallback; отмена пробрасывается вызывающему коду.
- AnswerV1, PublicAnalysisV1 и AnswerPresentationV1 строятся детерминированно. Findings не содержат свободного текста модели; summary/public items являются подмножеством тех же проверенных claims. Presentation имеет SHA-256 и ограничение размера.
- Safe fallback игнорирует все relations модели и публикует только точные excerpts из evidence pack с явным notice. Empty pack и empty idea возвращают no_evidence/clarification без inference и findings.
- Ветка схемы и renderer явно не доказывают semantic entailment relation цитатой; качество классификации требует отдельной offline/ручной оценки.

## Проверки

- `pytest -q tests/unit/test_analyst.py tests/unit/test_evidence_pack.py` — 22 passed.
- `pytest -q tests/unit` — 66 passed.
- `ruff check src/app/domain/contracts.py src/app/services/analyst.py tests/unit/test_analyst.py` — clean.
- `mypy src/app/services/analyst.py src/app/domain/contracts.py` — no issues.

Тесты проверяют точную цитату на русском с supplementary Unicode emoji, mismatched IDs/documents/offsets, unresolved features, запрещённые дополнительные поля, uncertain/conflicting relations, единственную repair-попытку, fallback без rejected relations, timeout/cancel и no-evidence.
