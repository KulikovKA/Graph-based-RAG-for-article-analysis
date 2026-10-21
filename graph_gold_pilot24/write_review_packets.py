"""Readable review artifacts from the curated JSONL, with no semantic generation."""
import csv
import json
from pathlib import Path

from validate_annotations import read_jsonl

BASE = Path(__file__).resolve().parent
sources = {s['document_code']: s for s in read_jsonl(BASE / 'pilot24_sources.jsonl')}
results = json.loads((BASE / 'annotations/reports/structural_validation.json').read_text(encoding='utf-8'))
vocab = json.loads((BASE / 'annotations/reviews/relation_vocabulary.json').read_text(encoding='utf-8'))


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
        'Один общий нерешённый вопрос Q1: утверждение словаря/рубрик. UNRESOLVED assertions: 0; это не означает утверждения схемы или gold.', '',
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
    (BASE / 'annotations/reviews' / (code + '_review.md')).write_text('\n'.join(lines) + '\n', encoding='utf-8')

with (BASE / 'pilot24_manifest.csv').open(encoding='utf-8-sig') as f:
    manifest = list(csv.DictReader(f))
progress = []
for m in manifest:
    r = next((r for r in results if r['document_code'] == m['document_code']), None)
    progress.append(dict(document_code=m['document_code'], document_id=m['document_id'],
        revision_id=m['revision_id'], split=m['split'],
        annotation_status='AI_DRAFT_PENDING_SCHEMA_APPROVAL' if r else 'NOT_STARTED',
        human_review='NOT_REVIEWED', source_chunks=len(sources[m['document_code']]['chunks']),
        mentions=r['mentions'] if r else None, assertions=r['assertions'] if r else None,
        counts_status='DRAFT_COUNTS' if r else 'NOT_MEASURED'))
(BASE / 'annotations/reports/progress.json').write_text(json.dumps(progress, indent=2) + '\n', encoding='utf-8')

lines = ['# GRAPH-GOLD-PILOT24 — checkpoint 2026-10-21', '',
    '**Работа не завершена: первичный проход 2/24, human gold 0/24.**', '',
    '## Источники', '',
    'Проверены все 24 документа, 24 ревизии, 35 chunks и split 12/6/6. Архив подготовки распакован без изменения его пяти файлов.', '',
    'Исходные тексты взяты без восстановления из hash-verified corpus_export.json от 2026-10-02. Затем все выбранные source-поля сверены с работающей PostgreSQL: полное совпадение. Подробности: `source_integrity.json` (первичная offline-проверка) и `live_source_verification.json` (последующая live-проверка, заменяет первоначальный статус недоступности БД).', '',
    'Глобальный snapshot `5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0` независимо пересчитан по сохранённому snapshot. Его файл не изменён. Source artifact SHA-256 сверён с artifact_hashes.json. Хеши revisions и chunks и соответствие section offsets проверены.', '',
    'Docker Engine 29.2.1 доступен; запущен только сервис postgres. Предоставленный export_pilot24.py был вызван через обёртку с read-only транзакциями. TCP-подключение отклонено: password authentication failed for user article_app. Пароль из .env корректно экранирован и совпадает с окружением существующего контейнера, но не принимается ролью в сохранённой базе. Пароль не менялся. Альтернативная SELECT-сверка выполнена через локальный Unix socket в REPEATABLE READ READ ONLY.', '',
    'Ollama, LightRAG, worker и extraction pipelines не запускались. Model facts/predictions не выводились в контекст разметки и не использовались для меток. Snapshot целиком хешировался программно; его facts не использовались как источники annotations.', '',
    '## Первичный проход', '']
lines += table(['Document', 'Chunks', 'Sentences', 'Mentions', 'Assertions', 'Concepts', 'Identity', 'Validation', 'Human review'], [
    [r['document_code'], r['chunks'], r['sentences'], r['mentions'], r['assertions'], r['canonical_concepts'], r['identity_decisions'], r['status'], r['human_review']] for r in results])
lines += ['', 'Все 13 предложений прочитаны в source-only AI-проходе. Spans включают повторные и вложенные упоминания; численные qualifiers сохраняют source evidence и attachment. Неизвестные параметры не дополнены догадками.', '',
    'Общий вопрос Q1 — согласование словаря 16 predicates и границ rubric. Он отмечен UNRESOLVED в обеих карточках, но это **один** вопрос, не два разных технических спора. Нерешённых assertion candidates нет: явно неподтверждённые отношения не создавались.', '',
    'Заявленная exhaustive-разметка — результат AI-прохода, а не измеренная полнота gold. Синтаксическая валидация не подтверждает семантику. Независимый primary/secondary human review не проводился, подписи null. Каталог gold пуст.', '',
    '## Следующий шаг', '',
    'Согласовать Q1 в reviews/questions.md, записать фактический ответ в adjudication_decisions.jsonl и применить необходимые изменения. Только затем переходить к остальным 10 DEV. После DEV заморозить rubric; CALIBRATION и HOLDOUT размечать отдельно. Проверка publication/author/family duplicates до закрытия HOLDOUT ещё не выполнена. HOLDOUT не использован для настройки правил.', '',
    '## Воспроизведение', '',
    'Из корня репозитория:', '',
    '```powershell',
    '.\\.venv\\Scripts\\python.exe graph_gold_pilot24/prepare_archived_sources.py',
    '.\\.venv\\Scripts\\python.exe graph_gold_pilot24/verify_live_socket.py',
    '.\\.venv\\Scripts\\python.exe graph_gold_pilot24/validate_annotations.py',
    '.\\.venv\\Scripts\\python.exe graph_gold_pilot24/write_review_packets.py',
    '```', '',
    '`build_dev_pair.py` содержит вручную заданные AI-решения и воспроизводит первичный draft; не использовать его для перезаписи будущей human-adjudicated версии. Семантический анализ не является результатом regex/extraction pipeline: поиск текста используется только для вычисления offsets заранее выбранных spans.', '']
(BASE / 'annotations/reports/CHECKPOINT.md').write_text('\n'.join(lines), encoding='utf-8')
print('Wrote two review packets, checkpoint report and 24-document progress inventory.')
