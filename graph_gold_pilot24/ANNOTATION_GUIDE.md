# Pilot-24: правила аннотации технического графа

Статус: **подготовка**, не gold-разметка. Тексты EvidenceChunks пока не экспортированы; никаких меток сущностей/отношений не назначено. Основа — `docs/analysis/GRAPH_RESEARCH_001_PART1/EVAL001_COMPARISON_DESIGN.md`.

## Выборка и независимость

24 frozen OpenAlex abstracts; `DEV=12`, `CALIBRATION=6`, `HOLDOUT=6`. Включены 8 historical Hybrid zero-concept документов, обзорные/экспериментальные/теоретические работы и разные классы технических задач. Похожие пары D060/D078 и D035/D092 сгруппированы в DEV; по опубликованному `nearest_documents.csv` среди выбранных документов не обнаружены cross-split пары с similarity >=0.80 (это не доказывает отсутствие общих author/document families). **Перед фиксацией holdout проверить publication/author/family duplicates по metadata**, а также пары вне nearest-neighbor export.

Gold нужно создавать **из исходных chunks**, а не из вывода HYBRID/LightRAG/GraphFacts. При оценке annotate все подходящие mentions/assertions, включая случаи, которые пропускают модели.

## Сущности / mentions

Каждая сущность: `mention_id`, `chunk_id`, `[start,end)` (Python Unicode codepoints относительно `chunk.text`), exact `surface_text` (`chunk.text[start:end] == surface_text`), `kind`, `contextual_role`, `canonical_concept`, `coreference_group`, `evidence_span_ids`, `annotation_status`.

Онтология v1: MATERIAL, DEVICE, PROPERTY, PERFORMANCE, ANALYTE, PROCESS, MECHANISM, OPERATING_CONDITION, MORPHOLOGY, TECHNOLOGY, APPLICATION, OTHER. Возможные дополнительные категории/роли сначала согласовать на DEV, затем заморозить rubric.

Не приписывать канонический NO2 там, где написано только `gas`; GO != rGO; graphene != graphene oxide; использованное вещество != измеряемый газ.

## Relations / assertions

Каждая связь: `assertion_id`, `head_mention_id`, `tail_mention_id`, направленный `relation_type`, `polarity` (`POSITIVE/NEGATIVE/UNKNOWN`), `modality` (`ASSERTED/PROPOSED/COMPARED/HYPOTHETICAL/UNKNOWN`), `qualifiers` (units, numeric values, range, temperature, humidity и т. п.), `evidence` как original chunk codepoint spans, `support_status` (`SUPPORTED/CONTRADICTED/INSUFFICIENT/UNRESOLVED`).

Отношения должны быть **source-scoped**, а не переноситься между документами из-за совпадения слова. Учитывать отрицания и «not only», сравнительные и фоновые утверждения, multiple entities одного типа, sentence/coreference scope и attachment условий к правильному relation.

Если relation не выражено в исходном тексте, не создавать его даже при высокой тематической вероятности. Отсутствие в abstract не равнозначно отсутствию свойства в полной статье.

## Canonical identity и linking

Label пары: `SAME`, `RELATED`, `BROADER`, `NARROWER`, `DIFFERENT`, `UNCERTAIN`. Нужны подтверждённые alias rules (например, локальное определение аббревиатуры), химические cannot-link ограничения, полный контекст. Не объединять concept-level SAME с instance-level техническими conditions.

## Полнота и проверка

Указать `annotation_scope`: например, все предложения этого chunk; отдельно `exhaustive_entities=true/false`, `exhaustive_relations=true/false`. Не отмечать неразмеченное как negative gold. Для нерешённых случаев `UNRESOLVED` с reason; не догадка.

Для gold-grade pilot нужен независимый human review; AI-assisted draft не объявлять человеческой ground truth. Желательно независимое второе мнение минимум на сложных cases и четверти обычных, с фиксацией разногласий и adjudication. Holdout не использовать для доработки prompt/rules и не открывать разработчикам архитектур метки.

## Порядок

1. Получить точные frozen chunks через read-only exporter.
2. Разметить D001/D010 (DEV) для проверки, что schema поддерживает типы/relations/qualifiers, и при необходимости дополнить rubric.
3. Разметить остальные DEV с исчерпывающим entity/relation recall в заданном scope.
4. Зафиксировать rubric/ontology; независимо разметить CALIBRATION и HOLDOUT, заблокировать labels последнего.
5. Только после готовности gold — обсуждать и менять EVAL-001 и тестировать A, B, F, C, D.
