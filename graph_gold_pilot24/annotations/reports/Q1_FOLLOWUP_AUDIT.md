# Дополнительный аудит D001/D010 после Q1

Дата: 2026-10-21. Рабочая рубрика: 0.2; human review документов **NOT_REVIEWED**.
Решение пользователя записано в `../reviews/adjudication_decisions.jsonl`.
Предыдущие drafts и правила сохранены в `../reviews/history/pre_q1_0.1/`.

| Документ | Assertions occurrences | Unique canonical triples | Qualified groups с сохранением качественного surface |
| --- | --- | --- | --- |
| D001 | 51 | 50 | 51 |
| D010 | 99 | 77 | 78 |

Ни одно обоснованное source mention не удалено: 61 и 105 соответственно.
Каждое assertion сохраняет исходное evidence. Полные группы с assertion IDs
находятся в `canonical_claim_audit.json`. Счётчики локальны документу.

## Семантические повторения

- D001: `sensor HAS_PROPERTY flexibility` повторяется в S2 и S6. Это один
  canonical triple. Формулировки `highly flexible` и `superior flexibility`
  различаются; surface сохраняется и qualified groups не сливаются автоматически.
  Не выводится численное превосходство из superior.
- D010: четыре связи состава четырёхкомпонентного nanocomposite с MXene, GO,
  CuO и ZnO встречаются по шесть раз, включая описание смеси и повторные формулы.
  Они дают четыре unique triples вместо 24 occurrences.
- D010: `sensor USES_MATERIAL nanocomposite` и `sensor DETECTS ammonia` повторяются
  по два раза. Conditions проверяются отдельно; одинаковый triple не означает
  идентичность физических образцов или равенство концентраций испытания.
- Concept-level объединения не распространяются на оптимальную конфигурацию
  датчика как отдельный instance. Proposed mechanism и asserted results не сливаются.
- Всего повторных core occurrences: D001 — 1, D010 — 22. Qualified grouping
  является вспомогательной диагностикой, а не окончательной matching policy scorer.

## Attachment room-temperature в D001

Исходный S4:

> The as-prepared fiber demonstrates sensitive sensing response, excellent long-term stability (84 days), low theoretical detection limit (43.5 ppb NO 2 ), great mechanical deformation tolerance (3000 bending cycles, 1000 twisting cycles and 65% strain strength), and washing durability in room-temperature gas detection.

Конечный modifier относится к gas detection. Он не устанавливает температуру
стирки или отдельного испытания washing durability. Температурный qualifier снят
с washing durability, response, stability и theoretical LOD. Исходное предложение
остаётся в evidence полностью. Room-temperature сохранён только у газового
детектирования (DETECTS NO2 / USED_FOR gas detection). Численная температура неизвестна.
Числа 84 days, 43.5 ppb, 3000/1000 cycles, 65% не изменены и не перепривязаны.

## Качественное best в D010

> The Ti 3 C 2 Tx MXene/GO/CuO/ZnO nanocomposite gas sensor exhibited the best NH 3 gas sensor.

Сохранено HAS_PERFORMANCE с exact surface `best`, modality COMPARED и concept
`best NH3 sensor (unspecified comparison metric)`. Нет числа, percentage improvement,
конкретной comparison metric или придуманной pairwise comparison. Следующие
96%/200 ppm/4.1 ppm не используются как подразумеваемые основания best.

## Механизм и статус

Гетеропереходы имеют MORPHOLOGY / electronic_interface, электронные слои —
MORPHOLOGY / electronic_charge_region; modulation — MECHANISM. Все 12 assertions,
включающие описание механизма S7 (включая три вложенных компонента), имеют PROPOSED.
SUPPORTED относится к наличию авторской гипотезы в тексте. Ни слои, ни гипотеза
не объявляются независимо изготовленными DEVICE или доказанным механизмом.

Один групповой IMPROVES D001 сохранён. Схема содержит прежние 16 predicates,
утверждённые только для DEV; frozen=false. Q1 закрыт только как schema decision.
Gold пуст, primary/secondary human annotator null. Проверки offsets, UUID,
evidence, qualifiers и типов направлений повторно пройдены.
