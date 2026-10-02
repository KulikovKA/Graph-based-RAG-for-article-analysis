# Проверка итогового audit bundle

Проверка 2026-10-02 завершилась успешно. Зафиксированные ниже read-only результаты относятся к выполнению аудита до отдельного запроса на commit/push. Production tests не запускались: эта задача требует read-only доступ к существующим services, а менялись только analysis artifacts.

- PostgreSQL export выполнен в repeatable-read READ ONLY transaction с ROLLBACK; `transaction_read_only=on` подтверждён.
- Exact manifest: 100 document/revision pairs и все 417 frozen fact IDs/keys совпали с PostgreSQL. Итоговый SELECT повторно подтвердил active docs100, facts417, states100, chunks136.
- Все 136 chunk SHA-256, section spans и nonwhitespace normalized abstract coverage прошли offline validation. Все 417 GraphFact offsets/normalized target substrings согласованы с source chunks.
- Qdrant: только GET metadata и POST points/scroll; 136 существующих vectors соответствуют всем frozen chunk IDs. Индекс не изменялся. Primary cosine и alternate pooling воспроизводятся offline.
- Neo4j: только MATCH/RETURN через execute_read; 509 baseline nodes и417 edges; frozen fact IDs и endpoints совпали с PG.
- CSV completeness: topic rows100 с unique document IDs; nearest rows300, каждый документ имеет ranks1/2/3 безself; pairwise rows4,950; manual pair rows30; concept rows124; zero rows11; feature rows409.
- Feature CSV keys уникальны; rows покрывают все417 frozen facts ровно один раз. Representative quote каждой feature совпадает с slice соответствующего source chunk. Granularity CSV содержит тот же полный409-row audit.
- Все248 manual concept quote anchors соответствуют exact Unicode slices. Selected fact references существуют в frozen corpus. Все30 examined pairs имеют0 exact shared features.
- Дополнительный peer QA подтвердил topic relatedness и scope/negation/broader cautions. Supplemental selected mappings не используются как extractor recall или причинные доли.
- Все10 обязательных файлов существуют; локальные relative links и artifact hashes проверены. Git status показывает только новые `docs/analysis/` и `scripts/analysis/`; tracked production files не имеют diff.

Во время аудита не выполнялись ingestion/backfill, source fetch, model inference/download, LightRAG initialization/native extraction, migrations, schema/index mutation или commit. При последующей публикации полные выгрузки корпуса, векторов и Neo4j исключены из Git; публикуются результаты анализа и scripts. Read-only guards относятся к реально выполненным обращениям; экспертная semantic разметка остаётся single-rater AI assessment с peer QA, а не независимым предметным gold.
