# Покрытие онтологии 24 AI drafts

Фиксированная схема: `pilot24-rubric-0.3-AUTO-FROZEN`; принятых типов 18; использовано 18.

Новые типы не добавлялись по CALIBRATION/HOLDOUT. Человеческое окончательное утверждение схемы отсутствует.

| Relation | Occurrences |
| --- | --- |
| HAS_PROPERTY | 97 |
| HAS_PERFORMANCE | 96 |
| USED_FOR | 81 |
| HAS_COMPONENT | 77 |
| USES_MATERIAL | 46 |
| FABRICATED_BY | 35 |
| HAS_MORPHOLOGY | 33 |
| HAS_MEMBER | 31 |
| DETECTS | 26 |
| ACTS_ON | 16 |
| HAS_MECHANISM | 9 |
| IMPROVES | 8 |
| MECHANISM_INVOLVES | 8 |
| FACILITATES | 7 |
| FUNCTIONS_AS | 6 |
| OPTIMIZES | 4 |
| INTEGRATED_IN | 2 |
| LOCATED_IN | 2 |

## Предложения только по DEV

| New predicate | Open questions |
| --- | --- |
| EXPLAINS | 4 |
| CAUSES | 3 |
| INCREASES | 2 |
| DEPENDS_ON | 2 |
| MEETS_REQUIREMENT | 1 |
| DOMINATES | 1 |

## Расширения domain/range существующих predicates

| Predicate | Open questions |
| --- | --- |
| HAS_MECHANISM | 4 |
| USED_FOR | 2 |
| HAS_PROPERTY | 1 |

Непокрытые классы: причинность и объяснение; направленное изменение; зависимости параметров; управление/переходы структуры; совместные требования; свойства структуры и механизмы материалов. Все конкретные исходники сохранены в questions.md; HOLDOUT evidence хранится отдельно.

Рекомендация для будущего human review: оценить новые предикаты CAUSES/EXPLAINS/INCREASES/DEPENDS_ON и узкие domain extensions на DEV, затем создать новую версию набора. Текущий проход завершён по прежним 18 типам; evaluation labels не использованы для расширения схемы.
