"""Readable review artifacts from the curated JSONL, with no semantic generation."""
import csv
import json
from pathlib import Path

from validate_annotations import read_jsonl

BASE = Path(__file__).resolve().parent
sources = {s['document_code']: s for s in read_jsonl(BASE / 'pilot24_sources.jsonl')}
results = json.loads((BASE / 'annotations/reports/structural_validation.json').read_text(encoding='utf-8'))
vocab = json.loads((BASE / 'annotations/reviews/relation_vocabulary.json').read_text(encoding='utf-8'))
canonical = {r['document_code']: r for r in json.loads((BASE / 'annotations/reports/canonical_claim_audit.json').read_text(encoding='utf-8'))}
pending_path = BASE / 'annotations/reviews/pending_source_cases.jsonl'
pending = read_jsonl(pending_path) if pending_path.exists() else []


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def table(headers, rows):
    return ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'] + [
        '| ' + ' | '.join(cell(v) for v in row) + ' |' for row in rows]


for report in results:
    code = report['document_code']
    d = read_jsonl(BASE / 'annotations/drafts' / (code + '.jsonl'))[0]
    concepts = {c['concept_id']: c for c in d['canonical_concepts']}
    mentions = {m['mention_id']: m for m in d['mentions']}
    spans = {s['span_id']: s for s in d['evidence_spans']}
    sentence_ids = {s['span_id']: s['sentence_id'] for s in d['sentence_review']}
    lines = [f'# {code} — {d["title"]}', '',
        '**AI draft; human review NOT_REVIEWED. Не gold.**', '',
        f'Document `{d["document_id"]}`; revision `{d["revision_id"]}`; split `{d["split"]}`.', '',
        'Область: все доступные frozen abstract chunks. Полный текст статьи не заявляется доступным.', '',
        f'Chunks: {report["chunks"]}; sentences: {report["sentences"]}; mentions: {report["mentions"]}; assertions: {report["assertions"]}; concepts: {report["canonical_concepts"]}; identity decisions: {report["identity_decisions"]}.', '',
        f'Структурная проверка: {report["status"]}. Семантическая проверка выполнена AI; независимой человеческой проверки не было.', '',
        f'Рубрика `{d["rubric_version"]}`. Q1 решён для рабочей схемы DEV; human review не предоставлен. Открытые вопросы: {", ".join(q["question_id"] for q in d["unresolved"]) or "нет"}.', '',
        f'Полнота AI-прохода: entities={d["exhaustive_entities"]}, relations={d["exhaustive_relations"]}. UNRESOLVED candidates: {report["unresolved_relation_candidates"]}; UNRESOLVED accepted assertions: {report["unresolved_assertions"]}.', '',
        f'Unique canonical triples: {canonical[code]["unique_canonical_triples"]}; qualified groups: {canonical[code]["unique_qualified_claims"]}. Source mentions/assertions не удалялись.', '',
        '## Полный доступный исходный текст', '']
    for c in sources[code]['chunks']:
        lines += [f'### Chunk {c["ordinal"]}: `{c["chunk_id"]}`', '',
                  f'Section `{c["section"]}`, section offsets [{c["section_start"]}, {c["section_end"]}); SHA-256 `{c["text_sha256"]}`.', '', c['text'], '']
    lines += ['## Проверка предложений', '']
    for s in d['sentence_review']:
        e = spans[s['span_id']]
        lines += [f'### {s["sentence_id"]}: [{e["start"]}, {e["end"]})', '', e['text'], '']
        lines += [n + '\n' for n in s['notes']]
    lines += ['## Все упоминания', '']
    lines += table(['Key', 'Sentence', 'Span', 'Exact surface', 'Kind / role', 'Canonical concept'], [
        [m['local_key'], m['sentence_id'], f'[{m["start"]}, {m["end"]})', m['surface_text'],
         m['kind'] + ' / ' + m['contextual_role'], concepts[m['canonical_concept']]['canonical_name']] for m in d['mentions']])
    lines += ['', '## Все утверждения', '', 'Направление каждой строки: head → tail. Полные UUID и evidence находятся в JSONL.', '']
    lines += table(['#', 'Head', 'Relation', 'Tail', 'Modality / scope', 'Qualifiers', 'Evidence sentences', 'Semantic note'], [
        [i, mentions[a['head_mention_id']]['local_key'], a['relation_type'], mentions[a['tail_mention_id']]['local_key'],
         a['modality'] + ' / ' + a['assertion_scope'], '; '.join(q['qualifier_type'] + ': ' + q['raw_text'] for q in a['qualifiers']),
         ', '.join(sentence_ids[e['span_id']] for e in a['evidence']), a.get('semantic_note', '')]
        for i, a in enumerate(d['assertions'], 1)])
    lines += ['', '## Все identity decisions', '']
    lines += table(['Left', 'Label', 'Right', 'Основание'], [
        [mentions[i['left_mention_id']]['local_key'], i['label'], mentions[i['right_mention_id']]['local_key'], i['reason']] for i in d['identity_decisions']])
    if d['unresolved']:
        lines += ['', '## Нерешённые кандидаты', '']
        for q in d['unresolved']:
            lines += [f'**{q["question_id"]}: {q["reason"]}**', '']
            lines += [s['text'] for s in q.get('evidence', [])]
            lines += ['', 'Варианты и перевод: `questions_Q2_Q3.md`. Кандидат не превращён в accepted assertion.', '']
    (BASE / 'annotations/reviews' / (code + '_review.md')).write_text('\n'.join(lines) + '\n', encoding='utf-8')

with (BASE / 'pilot24_manifest.csv').open(encoding='utf-8-sig') as f:
    manifest = list(csv.DictReader(f))
progress = []
for m in manifest:
    r = next((r for r in results if r['document_code'] == m['document_code']), None)
    cases = [q for q in pending if q['document_code'] == m['document_code']]
    status = ('AI_DRAFT_PENDING_ONTOLOGY_QUESTION' if r['unresolved_questions'] else 'AI_DRAFT_PENDING_HUMAN_REVIEW') if r else ('SOURCE_CANDIDATE_PENDING_DECISION' if cases else 'NOT_STARTED')
    progress.append(dict(document_code=m['document_code'], document_id=m['document_id'],
        revision_id=m['revision_id'], split=m['split'],
        annotation_status=status,
        human_review='NOT_REVIEWED', source_chunks=len(sources[m['document_code']]['chunks']),
        mentions=r['mentions'] if r else None, assertions=r['assertions'] if r else None,
        counts_status='DRAFT_COUNTS' if r else 'NOT_MEASURED',
        exhaustive_entities=r['exhaustive_entities'] if r else False,
        exhaustive_relations=r['exhaustive_relations'] if r else False,
        unique_canonical_triples=canonical[m['document_code']]['unique_canonical_triples'] if r else None,
        source_case_question_ids=[q['question_id'] for q in cases]))
(BASE / 'annotations/reports/progress.json').write_text(json.dumps(progress, indent=2) + '\n', encoding='utf-8')

lines = ['# GRAPH-GOLD-PILOT24 — checkpoint 2026-10-21', '',
    f'**Работа не завершена: AI drafts {len(results)}/24; полный первичный проход без открытых вопросов {sum(not r["unresolved_questions"] for r in results)}/24; human gold 0/24.**', '',
    '## Источники', '',
    'Проверены все 24 документа, 24 ревизии, 35 chunks и split 12/6/6. Архив подготовки распакован без изменения его пяти файлов.', '',
    'Исходные тексты взяты без восстановления из hash-verified corpus_export.json от 2026-10-02. Затем все выбранные source-поля сверены с работающей PostgreSQL: полное совпадение. Подробности: `source_integrity.json` (первичная offline-проверка) и `live_source_verification.json` (последующая live-проверка, заменяет первоначальный статус недоступности БД).', '',
    'Глобальный snapshot `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0` независимо пересчитан по сохранённому snapshot. Его файл не изменён. Source artifact SHA-256 сверён с artifact_hashes.json. Хеши revisions и chunks и соответствие section offsets проверены.', '',
    'Docker Engine 29.2.1 доступен; запущен только сервис postgres. Предоставленный export_pilot24.py был вызван через обёртку с read-only транзакциями. TCP-подключение отклонено: password authentication failed for user article_app. Пароль из .env корректно экранирован и совпадает с окружением существующего контейнера, но не принимается ролью в сохранённой базе. Пароль не менялся. Альтернативная SELECT-сверка выполнена через локальный Unix socket в REPEATABLE READ READ ONLY.', '',
    'Ollama, LightRAG, worker и extraction pipelines не запускались. Model facts/predictions не выводились в контекст разметки и не использовались для меток. Snapshot целиком хешировался программно; его facts не использовались как источники annotations.', '',
    '## Первичный проход', '']
lines += table(['Document', 'Chunks', 'Sentences', 'Mentions', 'Assertions', 'Concepts', 'Identity', 'Validation', 'Human review'], [
    [r['document_code'], r['chunks'], r['sentences'], r['mentions'], r['assertions'], r['canonical_concepts'], r['identity_decisions'], r['status'], r['human_review']] for r in results])
lines += ['', f'В сохранённых drafts прочитаны все {sum(r["sentences"] for r in results)} предложений. Spans включают повторные и вложенные упоминания; qualifiers сохраняют source evidence и attachment. D003 содержит открытый кандидат отношения: exhaustive_relations=false.', '',
    'Q1 решён пользователем: рабочая DEV-рубрика 0.2, 16 predicates, frozen=false. Решение и уточнения записаны в adjudication_decisions.jsonl. Дополнительный аудит пары: Q1_FOLLOWUP_AUDIT.md; unique canonical triples: D001=50, D010=77. Температура не назначается washing durability; best остаётся качественным с неизвестной метрикой сравнения.', '',
    'Q2 (D003): оптимизация слоя настройкой лазерных параметров; pending predicate/domain decision. Q3 (D004): содействие физическим процессам; только source candidates, полный draft D004 не выполнен. Предложения predicates не внесены в принятый словарь. Источники, переводы и варианты: reviews/questions_Q2_Q3.md.', '',
    'Заявленная exhaustive-разметка — результат AI-прохода, а не измеренная полнота gold. Синтаксическая валидация не подтверждает семантику. Независимый primary/secondary human review не проводился, подписи null. Каталог gold пуст.', '',
    '## Следующий шаг', '',
    'Получить решения Q2/Q3, записать фактические ответы, завершить D003 и продолжить остальные DEV. После всех 12 DEV подготовить аудит покрытия и предложить окончательный словарь для утверждения перед CALIBRATION/HOLDOUT. Проверка publication/author/family duplicates до закрытия HOLDOUT ещё не выполнена. HOLDOUT не использован для настройки правил.', '',
    '## Воспроизведение', '',
    'Из корня репозитория:', '',
    '```powershell',
    '.\\.venv\\Scripts\\python.exe graph_gold_pilot24/prepare_archived_sources.py',
    '.\\.venv\\Scripts\\python.exe graph_gold_pilot24/verify_live_socket.py',
    '.\\.venv\\Scripts\\python.exe graph_gold_pilot24/validate_annotations.py',
    '.\\.venv\\Scripts\\python.exe graph_gold_pilot24/audit_canonical_claims.py',
    '.\\.venv\\Scripts\\python.exe graph_gold_pilot24/write_review_packets.py',
    '```', '',
    '`build_dev_pair.py` содержит вручную заданные AI-решения и воспроизводит первичный draft; не использовать его для перезаписи будущей human-adjudicated версии. Семантический анализ не является результатом regex/extraction pipeline: поиск текста используется только для вычисления offsets заранее выбранных spans.', '']
(BASE / 'annotations/reports/CHECKPOINT.md').write_text('\n'.join(lines), encoding='utf-8')
print(f'Wrote {len(results)} review packets, checkpoint report and 24-document progress inventory.')
