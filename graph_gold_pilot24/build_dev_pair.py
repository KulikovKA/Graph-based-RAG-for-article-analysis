"""Materialize explicitly curated D001/D010 annotations; not an extractor.

All semantic choices below were made from the frozen source sentences.
The helpers only anchor those choices, assign stable IDs and serialize drafts.
"""
import copy
import json
import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

BASE = Path(__file__).resolve().parent
VERSION = 'pilot24-dev-rubric-0.2-WORKING'
SOURCES = {d['document_code']: d for d in map(json.loads, (BASE / 'pilot24_sources.jsonl').read_text(encoding='utf-8').splitlines())}
TEMPLATES = {d['document_code']: d for d in map(json.loads, (BASE / 'gold_annotation_template.jsonl').read_text(encoding='utf-8').splitlines())}


def uid(s):
    return str(uuid5(NAMESPACE_URL, 'graph-gold-pilot24/' + s))


class Draft:
    def __init__(self, code):
        self.code, self.src = code, SOURCES[code]
        self.data = copy.deepcopy(TEMPLATES[code])
        self.data.update(annotation_status='AI_DRAFT_PENDING_REVIEW',
                         annotation_scope='ALL_FROZEN_ABSTRACT_CHUNKS',
                         exhaustive_entities=True, exhaustive_relations=True,
                         rubric_version=VERSION, openalex_id=self.src['openalex_id'],
                         title=self.src['title'], evidence_spans=[], canonical_concepts=[],
                         sentence_review=[], source_chunks=[],
                         completeness_status='AI_FIRST_PASS_ALL_SENTENCES; HUMAN_RECALL_REVIEW_PENDING')
        self.data['review'].update(human_review_status='NOT_REVIEWED',
                                   ai_assistance='Codex source-only curated draft',
                                   adjudication_status='SCHEMA_Q1_RESOLVED_ANNOTATIONS_NOT_REVIEWED',
                                   schema_decision_refs=['Q1'])
        self.sentences, self.mentions, self.concepts = {}, {}, {}
        self.current = None
        n = 0
        for c in self.src['chunks']:
            self.data['source_chunks'].append({k: c[k] for k in ('chunk_id', 'text_sha256', 'stored_chunk_hash', 'section', 'ordinal')})
            # Decimal points have no following space in these two abstracts.
            for match in re.finditer(r'.+?(?:\. (?=[A-Z])|\.$|$)', c['text']):
                text = match.group().rstrip()
                if not text:
                    continue
                n += 1
                key = f'S{n}'
                span = self.span(c, match.start(), match.start() + len(text), key)
                self.sentences[key] = span
                self.data['evidence_spans'].append(span)
                self.data['sentence_review'].append(dict(sentence_id=key, span_id=span['span_id'],
                    entity_pass='REVIEWED_BY_AI', relation_pass='REVIEWED_BY_AI',
                    semantic_review='SOURCE_ONLY_AI; NOT_HUMAN_VALIDATED', notes=[]))

    def span(self, chunk, start, end, key):
        return dict(span_id=uid(f'{self.code}/span/{key}'), document_id=self.src['document_id'],
                    revision_id=self.src['revision_id'], chunk_id=chunk['chunk_id'],
                    start=start, end=end, text=chunk['text'][start:end],
                    source_text_sha256=chunk['text_sha256'])

    def locate(self, surface, sentence, occurrence=1):
        s = self.sentences[sentence]
        starts = [m.start() for m in re.finditer(re.escape(surface), s['text'])]
        if len(starts) < occurrence:
            raise ValueError((self.code, sentence, surface, starts))
        if occurrence == 1 and len(starts) > 1:
            raise ValueError(('Explicit occurrence required', self.code, sentence, surface, starts))
        pos = starts[occurrence - 1] + s['start']
        c = next(c for c in self.src['chunks'] if c['chunk_id'] == s['chunk_id'])
        return c, pos, pos + len(surface)

    def ms(self, sentence, spec):
        self.current = sentence
        for line in spec.strip().splitlines():
            fields = line.strip().split('|')
            key, surface, kind = fields[:3]
            canonical = fields[3] if len(fields) > 3 and fields[3] else surface.lower()
            role = fields[4] if len(fields) > 4 else 'technical_' + kind.lower()
            occurrence = int(fields[5]) if len(fields) > 5 else 1
            # A signed occurrence explicitly permits repeated surface text.
            if occurrence < 0:
                s = self.sentences[sentence]
                starts = [m.start() for m in re.finditer(re.escape(surface), s['text'])]
                pos = starts[-occurrence - 1] + s['start']
                c = next(c for c in self.src['chunks'] if c['chunk_id'] == s['chunk_id'])
                start, end = pos, pos + len(surface)
            else:
                c, start, end = self.locate(surface, sentence, occurrence)
            span = self.span(c, start, end, 'mention/' + key)
            self.data['evidence_spans'].append(span)
            concept_id = uid(f'{self.code}/concept/{canonical}')
            self.concepts.setdefault(concept_id, dict(concept_id=concept_id, canonical_name=canonical,
                kind=kind, instance_scope=self.src['revision_id'], normalization_version=VERSION))
            mention = dict(mention_id=uid(f'{self.code}/mention/{key}'), chunk_id=c['chunk_id'],
                surface_text=surface, start=start, end=end, kind=kind, contextual_role=role,
                canonical_concept=concept_id, coreference_group=None,
                evidence_span_ids=[span['span_id']], annotation_status='AI_DRAFT', local_key=key,
                sentence_id=sentence)
            self.mentions[key] = mention
            self.data['mentions'].append(mention)

    def rel(self, head, relation, tail, sentences=None, qualifiers=(), modality='ASSERTED', scope='STUDY_RESULT', note=None):
        h, t = self.mentions[head], self.mentions[tail]
        ss = sentences or list(dict.fromkeys([h['sentence_id'], t['sentence_id']]))
        key = f'{head}/{relation}/{tail}'
        assertion_id = uid(f'{self.code}/assertion/{key}')
        qs = []
        for sentence, raw, qtype, value, unit in qualifiers:
            c, start, end = self.locate(raw, sentence)
            span = self.span(c, start, end, 'qualifier/' + key + '/' + qtype)
            self.data['evidence_spans'].append(span)
            qs.append(dict(qualifier_type=qtype, raw_text=raw, raw_value=value, normalized_value=None,
                           unit=unit, comparator='EXPLICIT_TEXT', applies_to_assertion_id=assertion_id,
                           evidence_refs=[span['span_id']], status='EXPLICIT'))
        a = dict(assertion_id=assertion_id, head_mention_id=h['mention_id'], tail_mention_id=t['mention_id'],
                 relation_type=relation, polarity='POSITIVE', modality=modality,
                 qualifiers=qs, evidence=[self.sentences[s] for s in ss], support_status='SUPPORTED',
                 assertion_scope=scope, annotation_status='AI_DRAFT', relation_vocabulary_status='DEV_WORKING_APPROVED')
        if note:
            a['semantic_note'] = note
        self.data['assertions'].append(a)

    def same(self, keys, reason, coref=False):
        first = self.mentions[keys[0]]
        for key in keys[1:]:
            other = self.mentions[key]
            self.identity(keys[0], key, 'SAME', reason)
            old_id = other['canonical_concept']
            other['canonical_concept'] = first['canonical_concept']
            if not any(m['canonical_concept'] == old_id for m in self.data['mentions']):
                self.concepts.pop(old_id, None)
        if coref:
            for key in keys:
                self.mentions[key]['coreference_group'] = uid(f'{self.code}/coreference/{keys[0]}')

    def component_mentions(self, outer_key, components, modality='ASSERTED'):
        outer = self.mentions[outer_key]
        for alias_key, surface in components:
            key = outer_key + '_' + alias_key
            alias = self.mentions[alias_key]
            offset = outer['surface_text'].index(surface)
            c = next(c for c in self.src['chunks'] if c['chunk_id'] == outer['chunk_id'])
            span = self.span(c, outer['start'] + offset, outer['start'] + offset + len(surface), 'mention/' + key)
            self.data['evidence_spans'].append(span)
            m = dict(mention_id=uid(f'{self.code}/mention/{key}'), chunk_id=c['chunk_id'],
                surface_text=surface, start=span['start'], end=span['end'], kind='MATERIAL',
                contextual_role='named_composite_constituent', canonical_concept=alias['canonical_concept'],
                coreference_group=None, evidence_span_ids=[span['span_id']], annotation_status='AI_DRAFT',
                local_key=key, sentence_id=outer['sentence_id'])
            self.mentions[key] = m
            self.data['mentions'].append(m)
            self.identity(alias_key, key, 'SAME', 'Local full-name/formula definition and explicitly named constituent; no equivalence of whole composite and constituent.')
            self.rel(outer_key, 'HAS_COMPONENT', key, modality=modality)

    def identity(self, left, right, label, reason):
        l, r = self.mentions[left], self.mentions[right]
        ss = list(dict.fromkeys([l['sentence_id'], r['sentence_id']]))
        self.data['identity_decisions'].append(dict(decision_id=uid(f'{self.code}/identity/{left}/{right}'),
            left_mention_id=l['mention_id'], right_mention_id=r['mention_id'], label=label,
            evidence=[self.sentences[s] for s in ss], reason=reason,
            annotation_status='AI_DRAFT', human_review_status='NOT_REVIEWED',
            cannot_link=label == 'DIFFERENT'))

    def note(self, sentence, note):
        next(s for s in self.data['sentence_review'] if s['sentence_id'] == sentence)['notes'].append(note)

    def save(self):
        self.data['canonical_concepts'] = list(self.concepts.values())
        path = BASE / 'annotations/drafts' / (self.code + '.jsonl')
        path.write_text(json.dumps(self.data, ensure_ascii=False) + '\n', encoding='utf-8')
        print(self.code, len(self.data['mentions']), 'mentions', len(self.data['assertions']), 'assertions', len(self.concepts), 'concepts')


def d001():
    d = Draft('D001')
    d.ms('S1', '''textiles|E-textiles|DEVICE|e-textile|background_device_class
cost|low cost|PROPERTY|low cost
weight|light weight|PROPERTY|light weight
compat|conformable compatibility with clothes|PROPERTY
clothes|clothes|OTHER|clothes|integration_host
wearable|wearable and portable smart electronics|APPLICATION''')
    for t in ('cost', 'weight', 'compat'):
        d.rel('textiles', 'HAS_PROPERTY', t, scope='BACKGROUND')
    d.rel('textiles', 'USED_FOR', 'wearable', scope='BACKGROUND')
    d.ms('S2', '''strategy|fabricating strategy|PROCESS
easy|easy-handing|PROPERTY
cost2|low cost|PROPERTY|low cost
scalable|scalable|PROPERTY|scalability
sensor|fiber gas sensor|DEVICE|study fiber gas sensor
conductive|conductive|PROPERTY|electrical conductivity
flex|highly flexible|PROPERTY|flexibility
stretch|mechanically stretchable/twisted|PROPERTY|mechanical stretchability and twistability
wearability|great wearability|PROPERTY|wearability
knit|knittability|PROPERTY|knittability''')
    d.rel('sensor', 'FABRICATED_BY', 'strategy')
    for t in ('easy', 'cost2', 'scalable'):
        d.rel('strategy', 'HAS_PROPERTY', t)
    for t in ('conductive', 'flex', 'stretch', 'wearability', 'knit'):
        d.rel('sensor', 'HAS_PROPERTY', t)
    d.ms('S3', '''sensor3|gas sensor|DEVICE|study fiber gas sensor
threads|cotton/elastic threads|MATERIAL|cotton/elastic threads|fabrication_template
available|commercially available|PROPERTY|commercial availability
templates|flexible/stretchable templates|OTHER|flexible/stretchable templates|template_function
template_flex|flexible/stretchable|PROPERTY|template flexibility/stretchability
layer_material|reduced graphene oxide/mesoporous zinc oxide nanosheets|MATERIAL|reduced graphene oxide/mesoporous zinc oxide nanosheets|sensing_material
rgo|reduced graphene oxide|MATERIAL|reduced graphene oxide|sensing_component
zno|mesoporous zinc oxide nanosheets|MATERIAL|mesoporous zinc oxide nanosheets|sensing_component
mesoporous|mesoporous|MORPHOLOGY|mesoporosity
sheets|nanosheets|MORPHOLOGY|nanosheet morphology
layers|sensing layers|DEVICE|sensing layer|functional_layer
fibers|conducting fibers|DEVICE|study fiber gas sensor''')
    d.rel('sensor3', 'USES_MATERIAL', 'threads', note='Template role, not analyte; slash retained without assuming a blend or two separate device instances.')
    d.rel('threads', 'FUNCTIONS_AS', 'templates')
    d.rel('threads', 'HAS_PROPERTY', 'available')
    d.rel('templates', 'HAS_PROPERTY', 'template_flex')
    d.rel('sensor3', 'USES_MATERIAL', 'layer_material')
    d.rel('layer_material', 'HAS_COMPONENT', 'rgo')
    d.rel('layer_material', 'HAS_COMPONENT', 'zno')
    d.rel('zno', 'HAS_MORPHOLOGY', 'mesoporous')
    d.rel('zno', 'HAS_MORPHOLOGY', 'sheets')
    d.rel('layer_material', 'FUNCTIONS_AS', 'layers')
    d.rel('sensor3', 'HAS_COMPONENT', 'layers')
    d.ms('S4', '''fiber4|as-prepared fiber|DEVICE|study fiber gas sensor
response|sensitive sensing response|PERFORMANCE|sensing response
stability|excellent long-term stability|PERFORMANCE|long-term stability
lod|low theoretical detection limit|PERFORMANCE|theoretical detection limit
no2|NO 2|ANALYTE|nitrogen dioxide|target_analyte
tolerance|great mechanical deformation tolerance|PERFORMANCE|mechanical deformation tolerance
bend|bending cycles|PROCESS|bending test
twist|twisting cycles|PROCESS|twisting test
strain|strain strength|PERFORMANCE|strain strength (source wording)
wash|washing durability|PERFORMANCE|washing durability
temp|room-temperature|OPERATING_CONDITION|room temperature
detection|gas detection|PROCESS|gas detection''')
    rt = ('S4', 'room-temperature', 'temperature', 'room temperature', None)
    d.rel('fiber4', 'HAS_PERFORMANCE', 'response')
    d.rel('fiber4', 'HAS_PERFORMANCE', 'stability', qualifiers=[('S4', '84 days', 'duration', 84, 'days')])
    d.rel('fiber4', 'HAS_PERFORMANCE', 'lod', qualifiers=[('S4', '43.5 ppb NO 2', 'detection_limit', 43.5, 'ppb'), ('S4', 'theoretical', 'estimation_status', 'theoretical', None)])
    d.rel('fiber4', 'DETECTS', 'no2', qualifiers=[rt], note='NO2 is explicitly attached to the theoretical detection limit; do not substitute an unspecified gas.')
    d.rel('fiber4', 'HAS_PERFORMANCE', 'tolerance', qualifiers=[('S4', '3000 bending cycles', 'bending_cycles', 3000, 'cycles'), ('S4', '1000 twisting cycles', 'twisting_cycles', 1000, 'cycles'), ('S4', '65% strain strength', 'strain', 65, '%')])
    d.rel('fiber4', 'HAS_PERFORMANCE', 'strain', qualifiers=[('S4', '65% strain strength', 'strain', 65, '%')], note='Retain unusual source wording strain strength; no conversion to tensile stress or failure strain.')
    d.rel('fiber4', 'HAS_PERFORMANCE', 'wash', note='Room-temperature modifies gas detection; no washing-test temperature is specified. Do not attach it to washing durability.')
    d.rel('fiber4', 'USED_FOR', 'detection', qualifiers=[rt])
    d.ms('S5', '''wearable_characteristics|repairability, reliability, stability, and practicability|PROPERTY|wearable characteristic bundle
repair|repairability|PROPERTY
reliability|reliability|PROPERTY
stability5|stability|PROPERTY|wearable stability
practicability|practicability|PROPERTY
methods|knotting the fractured fibers, incorporating multiple sensors in series/parallel and weaving multisensor array networks integrated into clothes|PROCESS|wearable improvement procedure bundle
knot|knotting the fractured fibers|PROCESS|knotting fractured fibers
fractured|fractured fibers|DEVICE|fractured sensing fibers
incorporate|incorporating multiple sensors in series/parallel|PROCESS|series/parallel sensor incorporation
sensors5|multiple sensors|DEVICE|multiple sensing devices
wiring|series/parallel|MORPHOLOGY|series/parallel sensor arrangement
weave|weaving multisensor array networks integrated into clothes|PROCESS|weaving sensor networks into clothes
network|multisensor array networks|DEVICE|multisensor array network
clothes5|clothes|OTHER|clothes|integration_host''')
    d.rel('methods', 'IMPROVES', 'wearable_characteristics', note='Collective claim only. The text does not give a one-to-one mapping of three methods to four characteristics.')
    for t in ('repair', 'reliability', 'stability5', 'practicability'):
        d.rel('wearable_characteristics', 'HAS_MEMBER', t)
    for t in ('knot', 'incorporate', 'weave'):
        d.rel('methods', 'HAS_MEMBER', t)
    d.rel('knot', 'ACTS_ON', 'fractured')
    d.rel('incorporate', 'ACTS_ON', 'sensors5')
    d.rel('weave', 'ACTS_ON', 'network')
    d.rel('sensors5', 'HAS_MORPHOLOGY', 'wiring')
    d.rel('network', 'INTEGRATED_IN', 'clothes5')
    d.note('S5', 'No invented respectively mapping: collective improvement preserved as two explicit coordinated bundles.')
    d.ms('S6', '''props|good sensing properties|PERFORMANCE|sensing performance
flex6|superior flexibility|PROPERTY|flexibility
applications|scalable applications|APPLICATION|scalable wearable fiber applications
fibers6|wearable fibers|DEVICE|study fiber gas sensor
monitor|monitoring of numerous human activities|APPLICATION|human activity monitoring
mobile|personal mobile electronics|APPLICATION
hmi|human–machine interactions|APPLICATION''')
    d.rel('fibers6', 'HAS_PERFORMANCE', 'props')
    d.rel('fibers6', 'HAS_PROPERTY', 'flex6')
    for t in ('applications', 'monitor', 'mobile', 'hmi'):
        d.rel('fibers6', 'USED_FOR', t, modality='HYPOTHETICAL', scope='OUTLOOK', note='The source says may provide; these applications are not demonstrated outcomes.')
    d.same(['sensor', 'sensor3', 'fibers', 'fiber4', 'fibers6'], 'The proposed/as-prepared fiber sensor and final wearable fibers refer back to the same described study platform; device instances are not merged across documents.', coref=True)
    d.same(['cost', 'cost2'], 'Same low-cost property concept; separate bearer assertions remain separate.')
    d.same(['flex', 'flex6'], 'Same flexibility property, intensity preserved in surface text.')
    d.same(['clothes', 'clothes5'], 'Same generic clothes concept, no claim of the same physical garment.')
    d.identity('rgo', 'zno', 'DIFFERENT', 'Explicitly named distinct constituents of the sensing layer.')
    d.identity('textiles', 'sensor', 'BROADER', 'E-textiles is the background device class; the described fiber gas sensor is a specific e-textile platform, not the class itself.')
    d.note('S4', '84 days attaches to stability, 43.5 ppb to theoretical NO2 LOD, bending/twisting/strain values to mechanical tolerance. No numerical room-temperature value is inferred.')
    d.note('S4', 'Q1 follow-up audit: removed room-temperature from individual performance assertions (response, stability, LOD, washing durability). It remains on gas detection only; the trailing modifier does not explicitly specify separate test conditions.')
    d.save()


def d010():
    d = Draft('D010')
    d.ms('S1', '''mxene|Ti 3 C 2 Tx Mxene|MATERIAL|Ti3C2Tx MXene
dim|Two-dimensional (2D)|MORPHOLOGY|two-dimensional morphology
application|gas sensing application|APPLICATION|gas sensing
snr|high signal-to-noise ratio|PERFORMANCE|signal-to-noise ratio
temp|room temperature|OPERATING_CONDITION|room temperature''')
    d.rel('mxene', 'HAS_MORPHOLOGY', 'dim', scope='BACKGROUND')
    d.rel('mxene', 'USED_FOR', 'application', scope='BACKGROUND')
    d.rel('mxene', 'HAS_PERFORMANCE', 'snr', scope='BACKGROUND', qualifiers=[('S1', 'room temperature', 'temperature', 'room temperature', None)])
    d.ms('S2', '''mixture|mixture|MATERIAL|study sensing mixture
nh3_material|NH 3|ANALYTE|ammonia|target_analyte|-1
go|graphene oxide|MATERIAL|graphene oxide
go_alias|GO|MATERIAL|graphene oxide
cuo|copper oxide|MATERIAL|copper oxide (CuO)
cuo_alias|CuO|MATERIAL|copper oxide (CuO)
zno|zinc oxide|MATERIAL|zinc oxide
zno_alias|ZnO|MATERIAL|zinc oxide
mxene2|Ti 3 C 2 Tx Mxene|MATERIAL|Ti3C2Tx MXene
sensor|NH 3 gas sensor|DEVICE|study NH3 gas sensor
nh3_2|NH 3|ANALYTE|ammonia|target_analyte|2
high|high-performance|PERFORMANCE|high sensing performance
temp2|room temperature|OPERATING_CONDITION|room temperature''')
    for t in ('go', 'cuo', 'zno', 'mxene2'):
        d.rel('mixture', 'HAS_COMPONENT', t)
    d.rel('sensor', 'USES_MATERIAL', 'mixture')
    d.rel('sensor', 'DETECTS', 'nh3_2', qualifiers=[('S2', 'room temperature', 'temperature', 'room temperature', None)])
    d.rel('sensor', 'HAS_PERFORMANCE', 'high')
    for t in ('go', 'cuo', 'zno'):
        d.rel(t, 'USED_FOR', 'nh3_material', scope='BACKGROUND', note='Explicit NH3 sensing-material role; USED_FOR records target function without inventing individual device measurements.')
    d.ms('S3', '''composites|nanocomposites|MATERIAL|investigated nanocomposite collection
mg|Mxene/GO|MATERIAL|MXene/GO|sensing_material|-1
mz|Mxene/ZnO|MATERIAL|MXene/ZnO|sensing_material|-1
mc|Mxene/CuO|MATERIAL|MXene/CuO
mgz|Mxene/GO/ZnO|MATERIAL|MXene/GO/ZnO|sensing_material|-1
mgc|Mxene/GO/CuO|MATERIAL|MXene/GO/CuO
mzc|Mxene/ZnO/CuO|MATERIAL|MXene/ZnO/CuO
mgzc|Mxene/GO/ZnO/CuO|MATERIAL|Ti3C2Tx MXene/GO/CuO/ZnO nanocomposite
hydro|hydrothermal method|PROCESS|hydrothermal synthesis
nh3_3|NH 3|ANALYTE|ammonia|target_analyte
materials3|sensing materials|MATERIAL|investigated nanocomposite collection
temp3|room-temperature|OPERATING_CONDITION|room temperature
sensors3|gas sensors|DEVICE|investigated room-temperature gas sensors''')
    variants = ('mg', 'mz', 'mc', 'mgz', 'mgc', 'mzc', 'mgzc')
    for t in variants:
        d.rel('composites', 'HAS_MEMBER', t)
        d.rel(t, 'FABRICATED_BY', 'hydro')
        d.rel(t, 'USED_FOR', 'nh3_3', qualifiers=[('S3', 'room-temperature', 'temperature', 'room temperature', None)], note='Explicit use as NH3 sensing material.')
    d.rel('sensors3', 'USES_MATERIAL', 'materials3')
    d.ms('S4', '''sensor4|Ti 3 C 2 Tx MXene/GO/CuO/ZnO nanocomposite gas sensor|DEVICE|study four-component nanocomposite gas sensor
material4|Ti 3 C 2 Tx MXene/GO/CuO/ZnO|MATERIAL|Ti3C2Tx MXene/GO/CuO/ZnO nanocomposite
best|best|PERFORMANCE|best NH3 sensor (unspecified comparison metric)
nh3_4|NH 3|ANALYTE|ammonia|target_analyte''')
    d.rel('sensor4', 'USES_MATERIAL', 'material4')
    d.rel('sensor4', 'DETECTS', 'nh3_4')
    d.rel('sensor4', 'HAS_PERFORMANCE', 'best', modality='COMPARED', note='Preserves qualitative best claim; no response/selectivity ranking metric or numeric advantage is supplied here.')
    d.ms('S5', '''ratios|weight ratios|PROPERTY|component weight ratio
mat5a|Ti 3 C 2 Tx MXene/GO/CuO/ZnO|MATERIAL|Ti3C2Tx MXene/GO/CuO/ZnO nanocomposite|sensing_material|-1
mat5b|Ti 3 C 2 Tx MXene/GO/CuO/ZnO|MATERIAL|Ti3C2Tx MXene/GO/CuO/ZnO nanocomposite|sensing_material|2
ratio|weight ratio|PROPERTY|component weight ratio|composition_ratio|2''')
    d.rel('mat5b', 'HAS_PROPERTY', 'ratio', qualifiers=[('S5', '9:1:5:5', 'mass_ratio', '9:1:5:5', None), ('S5', 'optimal', 'optimization_status', 'optimal', None)], note='Ordered components are Ti3C2Tx MXene : GO : CuO : ZnO from this sentence, despite the different listing order in S3. No mass percentages inferred.')
    d.ms('S6', '''sensor6|optimal Ti 3 C 2 Tx MXene/GO/CuO/ZnO based gas sensor|DEVICE|optimal four-component nanocomposite gas sensor
mat6|Ti 3 C 2 Tx MXene/GO/CuO/ZnO|MATERIAL|Ti3C2Tx MXene/GO/CuO/ZnO nanocomposite
resp|high response|PERFORMANCE|sensor response
nh3_6a|NH 3|ANALYTE|ammonia|target_analyte|-1
humidity|humidity independence|PERFORMANCE|humidity independence
rh|30–70%RH|OPERATING_CONDITION|relative humidity range 30–70%RH
linear|good linear relationship|PERFORMANCE|linear calibration relationship (variables unspecified)
r2|R 2|PERFORMANCE|coefficient of determination
lod|low limit of detection|PERFORMANCE|detection limit
sel|high selectivity|PERFORMANCE|NH3 selectivity
nh3_6b|NH 3|ANALYTE|ammonia|target_analyte|2
gases|gases/VOCs|ANALYTE|comparison gases/VOCs|comparison_analyte_group
form|formaldehyde|ANALYTE|formaldehyde|comparison_analyte
eth|ethanol|ANALYTE|ethanol|comparison_analyte|-1
meth|methanol|ANALYTE|methanol|comparison_analyte
iso|isopropanol|ANALYTE|isopropanol|comparison_analyte
tol|toluene|ANALYTE|toluene|comparison_analyte
ace|acetone|ANALYTE|acetone|comparison_analyte''')
    d.rel('sensor6', 'USES_MATERIAL', 'mat6')
    d.rel('sensor6', 'HAS_PERFORMANCE', 'resp', qualifiers=[('S6', '96%', 'response', 96, '%'), ('S6', '200 ppm of NH 3', 'analyte_concentration', 200, 'ppm')])
    d.rel('sensor6', 'DETECTS', 'nh3_6a', qualifiers=[('S6', '200 ppm of NH 3', 'analyte_concentration', 200, 'ppm')])
    d.rel('sensor6', 'HAS_PERFORMANCE', 'humidity', qualifiers=[('S6', '30–70%RH', 'relative_humidity_range', [30, 70], '%RH')])
    d.rel('sensor6', 'HAS_PERFORMANCE', 'linear', qualifiers=[('S6', 'R 2 = 0.998', 'coefficient_of_determination', 0.998, None)], note='Source does not specify the fitted axes; do not add them.')
    d.rel('sensor6', 'HAS_PERFORMANCE', 'lod', qualifiers=[('S6', '4.1 ppm', 'detection_limit', 4.1, 'ppm')], note='No theoretical/experimental qualifier stated for this LOD.')
    d.rel('sensor6', 'HAS_PERFORMANCE', 'sel', modality='COMPARED', qualifiers=[('S6', 'NH 3 over several gases/VOCs including formaldehyde, ethanol, methanol, isopropanol, toluene, and acetone', 'selectivity_comparison', 'NH3 versus formaldehyde, ethanol, methanol, isopropanol, toluene, acetone', None)])
    for t in ('form', 'eth', 'meth', 'iso', 'tol', 'ace'):
        d.rel('gases', 'HAS_MEMBER', t)
        d.identity('nh3_6b', t, 'DIFFERENT', 'The source explicitly contrasts NH3 with this named comparison analyte; no inference of zero response.')
    d.note('S6', 'No NEGATIVE detects claims for comparison gases. 200 ppm belongs only to the 96% response observation; 30–70%RH belongs to humidity independence. R2 has unspecified fitted variables.')
    d.ms('S7', '''nh3_7|NH 3|ANALYTE|ammonia|target_analyte
mechanism|NH 3 -sensing mechanism|MECHANISM|proposed NH3 sensing mechanism
modulation|modulation of complex p–n heterojunctions|MECHANISM|p–n heterojunction modulation
junction|complex p–n heterojunctions|MORPHOLOGY|complex p–n heterojunction structure|electronic_interface
acc|electron accumulation layer|MORPHOLOGY|electron accumulation layer|electronic_charge_region
ntype|n-type|PROPERTY|n-type conductivity
gcz|GO/CuO/ZnO|MATERIAL|GO/CuO/ZnO subcomposite
dep|electron depletion layer|MORPHOLOGY|electron depletion layer|electronic_charge_region
ptype|p-type|PROPERTY|p-type conductivity
mxene7|Ti 3 C 2 Tx Mxene|MATERIAL|Ti3C2Tx MXene''')
    d.rel('sensor6', 'HAS_MECHANISM', 'mechanism', sentences=['S6', 'S7'], modality='PROPOSED')
    for t in ('modulation', 'acc', 'dep'):
        d.rel('mechanism', 'MECHANISM_INVOLVES', t, modality='PROPOSED')
    d.rel('modulation', 'MECHANISM_INVOLVES', 'junction', modality='PROPOSED')
    d.rel('acc', 'LOCATED_IN', 'gcz', modality='PROPOSED')
    d.rel('dep', 'LOCATED_IN', 'mxene7', modality='PROPOSED')
    d.rel('gcz', 'HAS_PROPERTY', 'ntype', modality='PROPOSED')
    d.rel('mxene7', 'HAS_PROPERTY', 'ptype', modality='PROPOSED')
    d.note('S7', 'Preserves author-proposed mechanism and author-stated n/p assignments. No claim that the mechanism is independently verified; no carrier type transferred to individual GO/CuO/ZnO constituents.')
    d.same(['mxene', 'mxene2', 'mxene7'], 'Repeated full Ti3C2Tx MXene name with case/spacing variation; background and proposed mechanism scopes remain distinct.')
    d.same(['go', 'go_alias'], 'Explicit local graphene oxide (GO) definition.')
    d.same(['cuo', 'cuo_alias'], 'Explicit local copper oxide (CuO) definition.')
    d.same(['zno', 'zno_alias'], 'Explicit local zinc oxide (ZnO) definition.')
    d.same(['nh3_material', 'nh3_2', 'nh3_3', 'nh3_4', 'nh3_6a', 'nh3_6b', 'nh3_7'], 'Repeated explicit NH3 chemical formula; roles and measurement instances remain scoped.')
    d.same(['mgzc', 'material4', 'mat5a', 'mat5b', 'mat6'], 'Same four explicitly named constituents; listing order does not change material concept. Ratio is attached only where supplied; no equality of tested sample instances.', coref=False)
    d.same(['mgzc', 'mixture'], 'S2 names the same four constituents as the four-component nanocomposite; concept identity does not fix their weight ratio.')
    d.same(['sensor4', 'sensor'], 'S2 introduces the four-component sensing mixture and its NH3 sensor; S4 repeats the full four-component sensor name. Optimal-ratio configuration remains separately scoped.', coref=True)
    d.same(['ratios', 'ratio'], 'Plural/singular component weight-ratio property, not equality of numeric ratios.')
    d.same(['temp', 'temp2', 'temp3'], 'Room-temperature wording; no numeric temperature inferred.')
    d.same(['composites', 'materials3'], 'Direct reference to the synthesized seven nanocomposites as sensing materials.', coref=True)
    for outer in variants:
        components = [('mxene', 'Mxene')]
        for key, surface in [('go', 'GO'), ('cuo', 'CuO'), ('zno', 'ZnO')]:
            if surface in d.mentions[outer]['surface_text']:
                components.append((key, surface))
        d.component_mentions(outer, components)
    for outer in ('material4', 'mat5a', 'mat5b', 'mat6'):
        d.component_mentions(outer, [('mxene', 'Ti 3 C 2 Tx MXene'), ('go', 'GO'), ('cuo', 'CuO'), ('zno', 'ZnO')])
    d.component_mentions('gcz', [('go', 'GO'), ('cuo', 'CuO'), ('zno', 'ZnO')], modality='PROPOSED')
    # Room temperature is stated for the whole tested sensor series in S3.
    # Carry that contextual condition with its original evidence, never 25 C.
    for a in d.data['assertions']:
        if a['head_mention_id'] == d.mentions['sensor6']['mention_id'] and a['relation_type'] in ('HAS_PERFORMANCE', 'DETECTS'):
            s = d.sentences['S3']
            c, start, end = d.locate('room-temperature', 'S3')
            span = d.span(c, start, end, 'qualifier/' + a['assertion_id'] + '/temperature')
            d.data['evidence_spans'].append(span)
            a['qualifiers'].append(dict(qualifier_type='temperature', raw_text='room-temperature',
                raw_value='room temperature', normalized_value=None, unit=None,
                comparator='EXPLICIT_TEXT', applies_to_assertion_id=a['assertion_id'],
                evidence_refs=[span['span_id']], status='EXPLICIT'))
            a['evidence'].insert(0, s)
    d.identity('sensor4', 'sensor6', 'BROADER', 'Optimal-ratio sensor is a specified configuration of the four-component sensor; instance-level SAME is deliberately not assumed.')
    for t in ('mg', 'mz', 'mc', 'mgz', 'mgc', 'mzc'):
        d.identity(t, 'mgzc', 'DIFFERENT', 'Different explicitly listed constituent set; retain separate composite concepts.')
    for left, right in [('go', 'cuo'), ('go', 'zno'), ('cuo', 'zno'), ('mxene', 'go')]:
        d.identity(left, right, 'DIFFERENT', 'Separately named chemical/material constituents, not aliases.')
    d.save()


if __name__ == '__main__':
    d001()
    d010()
