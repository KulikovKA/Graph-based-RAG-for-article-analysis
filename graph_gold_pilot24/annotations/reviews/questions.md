# Q1 — D001/D010: словарь отношений и границы рубрики

Статус: **UNRESOLVED — ожидается ответ пользователя**.
Не является решением человека или разрешением на массовую разметку.

Причина обращения: §4 и §7 задачи требуют согласовать недостающий контролируемый
словарь на первых двух DEV до остальных документов. Исследовательский дизайн
перечисляет поля relations, но не устанавливает конкретные predicates.

**Статьи:**

- D001 — Reduced Graphene Oxide/Mesoporous ZnO NSs Hybrid Fibers for Flexible,
  Stretchable, Twisted, and Wearable NO2 E-Textile Gas Sensor.
- D010 — Room-Temperature Ammonia Gas Sensor Based on Ti3C2Tx MXene/Graphene
  Oxide/CuO/ZnO Nanocomposite.

**Точный исходный фрагмент D001** (chunk `e9796bf6-68c8-440f-a814-ca185157cce3`, S5):

> More significantly, scalable wearable characteristics including repairability, reliability, stability, and practicability have been efficiently improved, which are achieved by knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes.

**Перевод и смысл:** ремонтопригодность, надёжность, стабильность и практическая
применимость улучшены совокупностью трёх приёмов. Привязка каждого приёма к
отдельному свойству не дана. Черновик сохраняет коллективное утверждение
`IMPROVES(группа процессов, группа свойств)` и `HAS_MEMBER` для членов групп.

**Точный исходный фрагмент D010** (chunk `761f757f-5005-4417-bf90-f2c5200f7600`, S7):

> The NH 3 -sensing mechanism was proposed based on the modulation of complex p–n heterojunctions via the electron accumulation layer in the n-type of GO/CuO/ZnO and the electron depletion layer in the p-type Ti 3 C 2 Tx Mxene.

**Перевод и смысл:** авторы предлагают объяснение чувствительности к NH3 через
модуляцию p–n-гетеропереходов и слои накопления/обеднения электронов.
Это предложенный механизм: modality `PROPOSED`, не установленный экспериментальный факт.

**Что требуется определить в схеме:** допустимы ли отдельные predicates
`HAS_MEMBER`, `MECHANISM_INVOLVES` и `LOCATED_IN`, а также включает ли `MORPHOLOGY`
пространственные электронные структуры. Исходный список entity kinds не задаёт
эту границу. Сама текстовая поддержка расположения слоёв не является спорной.

**Варианты:**

A. Принять словарь из 16 predicates в `relation_vocabulary.json` и рубрику 0.1:
`MORPHOLOGY` включает гетеропереходы и электронные слои; модуляция — `MECHANISM`.
`HAS_COMPONENT` только для физического состава, `HAS_MEMBER` для перечисленных групп.

B. Принять словарь, но гетеропереходы и электронные слои считать `DEVICE`
как функциональные компоненты. Тогда изменятся три entity kind и допустимые
endpoint kinds для соответствующих predicates; source spans и `PROPOSED` сохранятся.

C. Оставить словарь/границу категорий `UNRESOLVED` и пока не переходить к массовой разметке.

**Предварительное предложение:** A. Оно различает структуру и процесс её изменения
и не требует вводить новый entity kind. Это проект правила, а не вывод,
будто авторы статьи сами установили нашу онтологию.

**Вопрос:** какой вариант выбрать? Можно указать точечные изменения словаря.
Утверждение схемы не означает автоматического human review всех 150 assertions.
