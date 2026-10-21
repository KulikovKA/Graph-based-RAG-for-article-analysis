# Рабочая рубрика 0.2 — DEV

Статус: утверждена пользователем для DEV по Q1; **не заморожена**.
Версия: `pilot24-dev-rubric-0.2-WORKING`.
Базовые положения 0.1 сохранены, кроме явно изменённых ниже.
Решение схемы не является human review документов.

1. MORPHOLOGY включает геометрическую форму, электронные и межфазные структуры.
   p–n heterojunction получает contextual_role `electronic_interface`.
   Electron accumulation/depletion layer получает `electronic_charge_region`.
   Эти слои не самостоятельные DEVICE и не отдельно изготовленные покрытия.
   Heterojunction modulation — MECHANISM.
2. Все assertions предложенного механизма D010 сохраняют PROPOSED.
   SUPPORTED означает, что текст поддерживает именно авторскую гипотезу с этой
   modality; не доказанность гипотезы. Вложенные компоненты, упомянутые только
   внутри описания механизма, также сохраняют PROPOSED.
3. D001: один групповой IMPROVES и HAS_MEMBER для явно перечисленных групп.
   Нет декартова произведения методов/свойств и нет придуманного respectively.
4. 16 predicates утверждены только как рабочий DEV-словарь. Новые predicates
   или изменения допустимых endpoint kinds требуют решения в чате на конкретном
   источнике, если текущее представление теряет выраженное техническое отношение.
5. D001, S4: room-temperature явно характеризует gas detection. Оно остаётся
   у DETECTS и USED_FOR(gas detection). У отдельных HAS_PERFORMANCE (response,
   stability, theoretical LOD, washing durability) температура не назначается:
   отдельные условия соответствующих испытаний не описаны. Наличие фразы в
   evidence не даёт права автоматически прикрепить её ко всем утверждениям.
6. Качественное best D010 сохраняется как COMPARED без численного преимущества,
   установленной comparison metric или придуманной пары соперников. HIGH/LOW
   не заменяются численными thresholds. Определение конкретных показателей в
   следующем предложении не делает их автоматически основанием best.
7. Повторения учитываются на двух уровнях. Source mentions/assertions сохраняются.
   Отдельно рассчитываются документно-локальные unique canonical triples
   (head canonical concept, predicate, tail canonical concept) и qualified claims
   (дополнительно polarity, modality, assertion_scope, support_status, qualifiers
   и exact surface свойства/характеристики для сохранения качественных различий).
   Одинаковый triple не означает идентичность условий измерения или экземпляров.
   Составные qualitative qualifiers и units не теряются. Эти counts диагностические,
   окончательная matching policy будущего scorer ими не определяется.
8. Каждое утверждение сохраняет source evidence. Нерешённый кандидат нового
   predicate регистрируется UNRESOLVED отдельно от accepted assertions; это
   не отрицательный пример и не основание для exhaustive_relations=true.
9. Primary/secondary human annotator остаются null, human_review=NOT_REVIEWED.
   Согласование Q1 разрешает продолжение DEV, но не публикацию human gold.

После всех 12 DEV требуется сводный аудит покрытия и отдельное утверждение
окончательного словаря перед CALIBRATION/HOLDOUT.
