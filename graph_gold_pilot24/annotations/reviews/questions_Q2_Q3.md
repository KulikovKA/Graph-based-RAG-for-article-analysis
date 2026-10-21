# Новые вопросы DEV — Q2 / Q3

Оба вопроса UNRESOLVED; predicates не добавлены в принятый словарь.
Это выраженные в тексте отношения, которые текущие допустимые endpoints
не представляют без изменения схемы. Source support не подменяет approval ontology.

## Q2 — D003

**Статья:** Moisture-resistant, stretchable NOx gas sensors based on laser-induced graphene for environmental monitoring and breath analysis.

**Исходный фрагмент, S3:**

> Sandwiched between a soft elastomeric substrate and a moisture-resistant semipermeable encapsulant, the LIG sensing and electrode layer is first optimized by tuning laser processing parameters such as power, image density, and defocus distance.

**Контекст перед ним, S2:**

> This study presents the design and demonstration of a moisture-resistant, stretchable NO x gas sensor based on laser-induced graphene (LIG).

**Перевод и смысл:** чувствительный/электродный слой LIG оптимизируют настройкой
параметров лазерной обработки: мощности, плотности изображения и расстояния дефокусировки.
Назван объект оптимизации — слой, но не конкретная оптимизируемая метрика.

**Недостаток схемы:** IMPROVES сейчас направлен PROCESS → PROPERTY/PERFORMANCE.
Здесь endpoint — DEVICE. Подстановка выдуманной чувствительности вместо слоя
привнесла бы отсутствующее утверждение.

- A. Добавить `OPTIMIZES: PROCESS → DEVICE`: процедура оптимизирует
  названный объект; количественное улучшение и оптимизируемая метрика не предполагаются.
- B. Расширить `IMPROVES` на DEVICE, сохраняя `optimized_metric=UNKNOWN`
  и source wording; отдельный predicate не вводить.
- C. Оставить UNRESOLVED.

**Предварительное предложение:** A — точнее отражает слово optimized без
утверждения об измеренном улучшении конкретной характеристики.

Кандидат: tuning laser processing parameters → LIG sensing and electrode layer.
Он сохранён в D003.unresolved; exhaustive_relations=false.

## Q3 — D004

**Статья:** Microwave-Assisted Synthesis of Graphene–SnO2 Nanocomposites and Their Applications in Gas Sensors.

**Исходный фрагмент, S4:**

> By the microwave treatment of graphene–SnO 2 nanocomposites, with the graphene promoting efficient transport of the microwave energy, evaporation and redeposition of SnO x nanoparticles were facilitated.

**Следующее предложение, S5:**

> The graphene–SnO 2 nanocomposites exhibited a high sensor response of 24.7 for 1 ppm of NO 2 gas, at an optimized temperature of 150 °C.

**Перевод и смысл:** графен способствует эффективному переносу микроволновой
энергии; микроволновая обработка облегчает испарение и повторное осаждение SnOx.
Следующее измерение не используется как величина этих причинных эффектов.

**Недостаток схемы:** нужны MATERIAL → PROCESS и PROCESS → PROCESS.
`IMPROVES` их не допускает, `ACTS_ON` обозначает объект действия и не сохраняет
утверждение о содействии процессу.

- A. Добавить `FACILITATES: MATERIAL/PROCESS → PROCESS`: способствует процессу;
  не означает единственную, необходимую или достаточную причину.
- B. Расширить `IMPROVES` на эти endpoints с qualifier `effect=facilitation`,
  сохранив отсутствие количественной оценки.
- C. Оставить UNRESOLVED.

**Предварительное предложение:** A — соответствует promoting/facilitated и
сохраняет отличие от улучшения измеряемого показателя.

Кандидаты: graphene → microwave energy transport; microwave treatment → группа
evaporation/redeposition. Не создаётся добавочная причинная связь graphene →
evaporation только по цепочке. Модальность самого S4 — ASSERTED; последующее
We suggest из S7 не распространяется на S4 задним числом.

Q3 зарегистрирован в `pending_source_cases.jsonl`. Полная разметка D004 ещё
не выполнена; эти кандидаты не засчитаны как готовый документ или supported gold.
