"""Validate and report 24 AI drafts, keeping all HOLDOUT labels private."""
import csv
import hashlib
import itertools
import json
import re
from collections import Counter
from pathlib import Path

from audit_canonical_claims import audit
from campaign_paths import BASE,draft_paths,private_root
from validate_annotations import read_jsonl,validate


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    text=value.rstrip()+'\n' if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(text,encoding='utf-8');temp.replace(path)


def cell(x):return str(x).replace('|','\\|').replace('\n',' ')


def table(headers,rows):
    return ['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |']+[
       '| '+' | '.join(cell(x) for x in row)+' |' for row in rows]


TRANSLATIONS={
 'CAUSES':'В тексте описан причинный переход: исходный процесс/механизм приводит к указанному результату. FACILITATES не сохраняет эту более сильную формулировку.',
 'EXPLAINS':'Авторы связывают названную структуру, свойство или процесс с объяснением наблюдаемой характеристики. Текущая схема не содержит подходящего направленного отношения с такими endpoints.',
 'INCREASES':'Величина явно увеличивается под действием указанного фактора. Это направление изменения; оно не всегда равнозначно улучшению качества.',
 'DEPENDS_ON':'Значение характеристики явно зависит от структуры, конфигурации или параметра. Словарь не выражает такую зависимость.',
 'HAS_MECHANISM':'В тексте механизм относится к материалу, тогда как принятый HAS_MECHANISM допускает только DEVICE. Подмена материала устройством исказила бы тип.',
 'HAS_PROPERTY':'Свойство явно относится к структуре MORPHOLOGY, но у HAS_PROPERTY такой тип носителя не разрешён.',
 'DOMINATES':'Названное свойство определяет преобладающий вклад в перенос молекул. Это иной смысл, чем принадлежность свойства или действие на материал.',
 'USED_FOR':'Указано перспективное применение материала в названном устройстве. Текущие tail kinds USED_FOR не включают DEVICE; физический состав устройства не утверждён.',
 'MEETS_REQUIREMENT':'Отрицание относится к совместному выполнению двух требований: низкий шум И сильный сигнал. Нельзя превращать его в два независимых отрицания.',
 'TRANSITIONS_TO':'В ходе формирования меняется сам механизм роста: ion-by-ion growth переходит в particle-mediated crystallization.',
 'CONTROLS':'Условия роста позволяют кинетически контролировать внутреннюю архитектуру. PROCESS → MORPHOLOGY control не выражается OPTIMIZES технического объекта.',
 'AFFECTS':'Способ синтеза влияет на свойства материала; направление улучшения не указано, поэтому IMPROVES был бы сильнее исходного текста.',
 'INTEGRATED_IN':'Материал интегрирован с оптическим устройством; INTEGRATED_IN допускает только DEVICE в качестве head.'}


def questions_for(d):
    mentions={m['mention_id']:m for m in d['mentions']}
    for q in d['unresolved']:
        item=dict(q)
        item.update(document_code=d['document_code'],document_id=d['document_id'],revision_id=d['revision_id'],
                    split=d['split'],title=d['title'],human_review='NOT_REVIEWED')
        pred=q.get('proposed_relation_type')
        if pred:
            item['translation_and_meaning_ru']=TRANSLATIONS.get(pred,'Точное утверждение сохранено в evidence; оно не представимо допустимыми типами endpoints текущей схемы.')
            item['endpoint_examples']=[dict(head=mentions[c['head_mention_id']]['surface_text'],
                head_kind=mentions[c['head_mention_id']]['kind'],tail=mentions[c['tail_mention_id']]['surface_text'],
                tail_kind=mentions[c['tail_mention_id']]['kind'],modality=c['modality'],polarity=c['polarity']) for c in q.get('candidates',[])]
        elif q['category']=='NUMERIC_INTERPRETATION':
            item['translation_and_meaning_ru']='Начальные энергии отрицательные. Последующее increase в 9/13 раз не определяет, сравнивают ли авторы модуль энергии или её signed value. Численные eV значения не вычислялись из этих факторов.'
        else:
            item['translation_and_meaning_ru']='LIG в основном тексте обозначает материал, но в первом предложении метонимически описывает способ его получения. Не создано отношение синтеза материала самим собой.'
        yield item


def question_markdown(items,title):
    lines=['# '+title,'','Все открытые вопросы UNRESOLVED. Они не блокировали автоматический проход. Q1/Q2/Q3 решены пользователем и находятся в adjudication_decisions.jsonl.','']
    for q in items:
        lines += [f'## {q["question_id"]} — {q["document_code"]}', '',
                  f'**Статья:** {q["title"]}.', '',
                  f'Document `{q["document_id"]}`; revision `{q["revision_id"]}`; split `{q["split"]}`.', '',
                  '**Точный оригинал:**','']
        lines += ['> '+s['text'] for s in q['evidence']]
        lines += ['', '**Перевод и смысл:** '+q['translation_and_meaning_ru'],'',
                  '**Что неоднозначно/непокрыто:** '+q['reason'],'']
        for label,value in q.get('options',{}).items():lines += [f'{label}. {value}','']
        lines += ['**Предварительное предложение:** '+q.get('preliminary_recommendation','Сохранить источник без догадок.'),'']
        if q.get('endpoint_examples'):
            lines+=table(['Head','Proposed relation','Tail','Modality / polarity'],[
              [x['head'],q['proposed_relation_type'],x['tail'],x['modality']+' / '+x['polarity']] for x in q['endpoint_examples']])+['']
    return '\n'.join(lines)+'\n'


def review_packet(d,summary):
    ms={m['mention_id']:m for m in d['mentions']};cs={c['concept_id']:c for c in d['canonical_concepts']}
    lines=[f'# {d["document_code"]} — {d["title"]}','','**AI draft — HUMAN_REVIEW=NOT_REVIEWED; не human gold.**','',
      f'Document `{d["document_id"]}`, revision `{d["revision_id"]}`, split `{d["split"]}`, rubric `{d["rubric_version"]}`.','',
      f'Chunks {summary["chunks"]}; sentences {summary["sentences"]}; mentions {summary["mentions"]}; assertions {summary["assertions"]}; unique canonical triples {summary["unique_canonical_triples"]}; questions {summary["unresolved"]}; validation {summary["validation"]}.','',
      f'Полный AI-проход завершён. exhaustive_entities={d["exhaustive_entities"]}; exhaustive_relations={d["exhaustive_relations"]}; неразрешённые кандидаты не являются negative gold.','',
      '## Исходные frozen EvidenceChunks','']
    source=SOURCES[d['document_code']]
    for c in source['chunks']:lines += [f'### `{c["chunk_id"]}`', '',f'SHA-256 `{c["text_sha256"]}`, section `{c["section"]}`; [{c["section_start"]}, {c["section_end"]}).','',c['text'],'']
    lines+=['## Semantic self-audit','']+d['semantic_self_audit']['notes']+['','## Mentions','']
    lines+=table(['Key','Sentence','Span','Surface','Kind / role','Canonical'],[
       [m['local_key'],m['sentence_id'],f'[{m["start"]},{m["end"]})',m['surface_text'],m['kind']+' / '+m['contextual_role'],cs[m['canonical_concept']]['canonical_name']] for m in d['mentions']])
    lines+=['','## Assertions','']
    lines+=table(['Head','Relation','Tail','Polarity','Modality / scope','Qualifiers','Evidence span IDs'],[
      [ms[a['head_mention_id']]['local_key'],a['relation_type'],ms[a['tail_mention_id']]['local_key'],a['polarity'],a['modality']+' / '+a['assertion_scope'],
       '; '.join(q['qualifier_type']+': '+q['raw_text']+' → '+str(q['raw_value']) for q in a['qualifiers']),'; '.join(e['span_id'] for e in a['evidence'])] for a in d['assertions']])
    lines+=['','## Identity decisions','']
    lines+=table(['Left','Label','Right','Reason'],[
      [ms[i['left_mention_id']]['local_key'],i['label'],ms[i['right_mention_id']]['local_key'],i['reason']] for i in d['identity_decisions']])
    lines+=['','## Unresolved','',question_markdown(list(questions_for(d)),'Вопросы документа')]
    return '\n'.join(lines)+'\n'


SOURCES={d['document_code']:d for d in read_jsonl(BASE/'pilot24_sources.jsonl')}


def main():
    reports=BASE/'annotations/reports';reviews=BASE/'annotations/reviews';priv=private_root()
    with (BASE/'pilot24_manifest.csv').open(encoding='utf-8-sig') as f:manifest=list(csv.DictReader(f))
    templates={d['document_code']:d for d in read_jsonl(BASE/'gold_annotation_template.jsonl')}
    vocab=json.loads((reviews/'relation_vocabulary.json').read_text(encoding='utf-8'))
    freeze=json.loads((reports/'DEV_ONTOLOGY_FREEZE.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((reviews/'relation_vocabulary.json').read_bytes()).hexdigest()==freeze['vocabulary_sha256'],'Frozen vocabulary changed'
    assert hashlib.sha256((BASE/'annotation.schema.json').read_bytes()).hexdigest()==freeze['annotation_schema_sha256'],'Frozen JSON schema changed'
    drafts={};paths={}
    for p in draft_paths():
        d=read_jsonl(p)[0];assert d['document_code'] not in drafts
        drafts[d['document_code']]=d;paths[d['document_code']]=p
    assert set(drafts)=={m['document_code'] for m in manifest} and len(drafts)==24
    rows=[];allquestions=[];freq=Counter();newtypes=Counter();domain=Counter()
    for m in manifest:
        d=drafts[m['document_code']];errors=validate(d,SOURCES[m['document_code']],templates[m['document_code']],vocab)
        assert not errors,(d['document_code'],errors)
        assert d['mentions'] and d['assertions'] and d.get('semantic_self_audit')
        assert d['review']['human_review_status']=='NOT_REVIEWED'
        a=audit(d);qs=list(questions_for(d));allquestions+=qs
        freq.update(x['relation_type'] for x in d['assertions'])
        if d['split']=='DEV':
            for issue in qs:
                pred=issue.get('proposed_relation_type')
                if pred:(domain if pred in vocab['relations'] else newtypes).update([pred])
        summary=dict(document_code=d['document_code'],split=d['split'],chunks=len(SOURCES[d['document_code']]['chunks']),
          sentences=len(d['sentence_review']),mentions=len(d['mentions']),assertions=len(d['assertions']),
          unique_canonical_triples=a['unique_canonical_triples'],unique_qualified_claims=a['unique_qualified_claims'],
          canonical_concepts=len(d['canonical_concepts']),identity_decisions=len(d['identity_decisions']),
          unresolved=len(qs),unresolved_candidate_assertions=sum(len(q.get('candidates',[])) for q in qs),
          validation='PASS',human_review='NOT_REVIEWED',gold_status='NOT_APPROVED',
          draft_status='AI_FIRST_PASS_COMPLETE_WITH_UNRESOLVED' if qs else 'AI_FIRST_PASS_COMPLETE',
          exhaustive_entities=d['exhaustive_entities'],exhaustive_relations=d['exhaustive_relations'])
        rows.append(summary)
        packet=review_packet(d,summary)
        folder=priv/'reviews' if d['split']=='HOLDOUT' else reviews
        write(folder/(d['document_code']+'_review.md'),packet)
    publicq=[q for q in allquestions if q['split']!='HOLDOUT'];privateq=[q for q in allquestions if q['split']=='HOLDOUT']
    write(reviews/'questions.json',publicq);write(reviews/'questions.md',question_markdown(publicq,'Открытые вопросы DEV / CALIBRATION'))
    write(priv/'reviews/questions.json',privateq);write(priv/'reviews/questions.md',question_markdown(privateq,'Закрытые вопросы HOLDOUT'))
    write(priv/'reviews/all_questions.json',allquestions);write(priv/'reviews/all_questions.md',question_markdown(allquestions,'Все нерешённые вопросы — локальная закрытая копия'))
    write(reports/'summary_24.json',rows);write(reports/'progress.json',rows)
    with (reports/'summary_24.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    coverage=dict(rubric_version=vocab['version'],accepted_relation_types=18,used_relation_types=len(freq),
       relation_frequencies=dict(freq.most_common()),proposed_new_types_from_DEV=dict(newtypes),
       proposed_domain_extensions_from_DEV=dict(domain),dev_freeze_report='DEV_ONTOLOGY_FREEZE.json',
       unresolved_questions_by_split={s:sum(r['unresolved'] for r in rows if r['split']==s) for s in ['DEV','CALIBRATION','HOLDOUT']},
       evaluation_schema_modified=False,final_human_ontology_approval=False,
       limitation='Frequencies are occurrence counts. Unique triples reported separately. Evaluation gaps were recorded without changing accepted types.')
    write(reports/'ontology_coverage.json',coverage)
    lines=['# Покрытие онтологии 24 AI drafts','',f'Фиксированная схема: `{vocab["version"]}`; принятых типов 18; использовано {len(freq)}.','',
       'Новые типы не добавлялись по CALIBRATION/HOLDOUT. Человеческое окончательное утверждение схемы отсутствует.','']
    lines+=table(['Relation','Occurrences'],freq.most_common())+['','## Предложения только по DEV','']
    lines+=table(['New predicate','Open questions'],newtypes.most_common())+['','## Расширения domain/range существующих predicates','']
    lines+=table(['Predicate','Open questions'],domain.most_common())+['',
       'Непокрытые классы: причинность и объяснение; направленное изменение; зависимости параметров; управление/переходы структуры; совместные требования; свойства структуры и механизмы материалов. Все конкретные исходники сохранены в questions.md; HOLDOUT evidence хранится отдельно.','',
       'Рекомендация для будущего human review: оценить новые предикаты CAUSES/EXPLAINS/INCREASES/DEPENDS_ON и узкие domain extensions на DEV, затем создать новую версию набора. Текущий проход завершён по прежним 18 типам; evaluation labels не использованы для расширения схемы.','']
    write(reports/'ONTOLOGY_COVERAGE.md','\n'.join(lines))
    queue=[dict(document_code=r['document_code'],split=r['split'],human_review='NOT_REVIEWED',priority='HIGH' if r['unresolved'] else 'STANDARD',
        unresolved=r['unresolved'],review_scope='All mentions, all assertions and evidence; draft completeness not measured human recall',
        packet='PRIVATE_LOCAL_STORE' if r['split']=='HOLDOUT' else '../reviews/'+r['document_code']+'_review.md') for r in rows]
    write(reviews/'human_review_queue.json',queue)
    stats=dict(ai_drafts_complete=24,structural_pass=24,documents_with_unresolved=sum(r['unresolved']>0 for r in rows),
       unresolved_questions=len(allquestions),unresolved_candidate_assertions=sum(r['unresolved_candidate_assertions'] for r in rows),
       human_reviewed=0,approved_gold=0,mentions=sum(r['mentions'] for r in rows),assertions=sum(r['assertions'] for r in rows),
       unique_canonical_triples=sum(r['unique_canonical_triples'] for r in rows),sentences=sum(r['sentences'] for r in rows),chunks=sum(r['chunks'] for r in rows),
       public_drafts=18,private_holdout_drafts=6,split_counts={s:sum(r['split']==s for r in rows) for s in ['DEV','CALIBRATION','HOLDOUT']})
    write(reports/'final_status.json',stats)
    lines=['# GRAPH-GOLD-PILOT24 — полный автоматический проход','',
       f'**AI drafts 24/24; structural PASS 24/24; human review 0; approved human gold 0.**','',
       f'Mentions {stats["mentions"]}; assertion occurrences {stats["assertions"]}; unique canonical triples {stats["unique_canonical_triples"]}; source chunks {stats["chunks"]}; reviewed sentences {stats["sentences"]}.','',
       f'UNRESOLVED: {stats["unresolved_questions"]} вопросов в {stats["documents_with_unresolved"]} документах; {stats["unresolved_candidate_assertions"]} relation candidates. Наличие вопросов не блокировало проход.','']
    lines+=table(['Document','Split','Chunks','Mentions','Assertions','Unique canonical triples','Unresolved','Validation'],[
       [r[k] for k in ['document_code','split','chunks','mentions','assertions','unique_canonical_triples','unresolved','validation']] for r in rows])
    lines+=['','## Источники и независимость','',
       '24 frozen revisions / 35 original EvidenceChunks сверены с manifest, хешами архива и live PostgreSQL через read-only socket. Глобальный snapshot hash пересчитан; исходные файлы не заменены. Подробности source_integrity.json и live_source_verification.json.','',
       'Аннотации выполнены по исходным текстам. Ollama и сравниваемые extraction pipelines не запускались; predictions не использовались. Источники ограничены abstracts: полнота статей не заявляется.','',
       '## Схема, вопросы и качество','',
       'Q1/Q2/Q3 применены в рубрике 0.3. После DEV закреплены 18 predicates; непокрытие сохранено отдельно. Отчёт DEV_ONTOLOGY_FREEZE.json содержит ограничение хронологии: первая запись freeze не удалась, CALIBRATION text был показан до повторной успешной записи; принятые определения не менялись по evaluation text.','',
       'JSON Schema, Unicode offsets, exact evidence, UUID, endpoints, directions, qualifier attachment, source hashes, sentence coverage и canonical conflicts проверены. Каждый документ прошёл AI semantic self-audit отдельно от structural validation. Это не независимая проверка истинности и не доказательство идеального recall.','',
       'Качественные best/high не получили придуманных чисел; proposed mechanisms и вычислительные результаты сохраняют свою область действия; отрицания и not only обработаны по контексту. Повторные source occurrences сохранены; counts canonical triples и qualified claims доступны отдельно.','',
       'Все вопросы DEV/CALIBRATION: ../reviews/questions.md. Полный локальный список, включая HOLDOUT, находится в закрытом каталоге. Все 24 документа требуют human review: ../reviews/human_review_queue.json.','',
       '## Раздельное хранение и ограничения','',
       '18 drafts и несекретные отчёты находятся в репозитории. 6 HOLDOUT drafts, их specifications, evidence-bearing review packets, вопросы и подробные triple audits находятся вне репозитория. В публичных артефактах HOLDOUT представлен только техническими counts/status. Gold пуст.','',
       'Риск publication/author/family leakage проверяется в leakage_audit.json. Общий автор не доказывает дубликат; отсутствие совпадений не доказывает независимость семейств. Итоговые результаты ещё не являются confirmatory evaluation.','',
       '## Возобновление','',
       'Файлы каждого завершённого draft сохранены отдельно. Не перегенерировать готовые labels без необходимости; повторная валидация: python graph_gold_pilot24/validate_annotations.py. Пересчёт отчётов: python graph_gold_pilot24/audit_canonical_claims.py и python graph_gold_pilot24/finalize_campaign.py. Private HOLDOUT location задаётся локальным ignored-файлом или стандартным закрытым каталогом профиля пользователя.','']
    write(reports/'FINAL_REPORT.md','\n'.join(lines))
    write(reports/'CHECKPOINT.md','# Текущий checkpoint\n\nПолный автоматический проход завершён: 24/24. Актуальные counts, ограничения и вопросы: [FINAL_REPORT.md](FINAL_REPORT.md). Human review / approved gold: 0.\n')
    print(json.dumps(stats,ensure_ascii=False))


if __name__=='__main__':main()
