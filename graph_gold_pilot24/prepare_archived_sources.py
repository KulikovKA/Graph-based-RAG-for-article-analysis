"""Select original frozen chunks from the hash-verified read-only audit export.

Offline fallback when PostgreSQL is unavailable. Never reads model predictions
as annotation input; the full snapshot is hashed only for integrity validation.
Run from the repository root. Existing differing outputs are never overwritten.
"""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from uuid import UUID

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
EXPECTED = '5b80378fa2d8312951446fcbb3ada7994d775f13d452ff08fd415377a5fcade0'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stable(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(',', ':')).encode('utf-8'))


def save_new(path, text):
    data = text.encode('utf-8')
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'Refusing to overwrite differing file: {path}')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as f:
            f.write(data)


def main():
    audit = ROOT / 'docs/analysis/GRAPH_CORPUS_AUDIT'
    archive = audit / 'corpus_export.json'
    hashes = json.loads((audit / 'artifact_hashes.json').read_text(encoding='utf-8'))
    archive_hash = sha(archive.read_bytes())
    assert archive_hash == hashes['corpus_export.json'], 'Archive artifact hash mismatch'
    source = json.loads(archive.read_text(encoding='utf-8'))
    assert source['transaction_read_only'] == 'on'
    snap_path = ROOT / 'data/checkpoints/graph002-live-20261002.snapshot.json'
    snapshot = json.loads(snap_path.read_text(encoding='utf-8'))['snapshot']
    assert stable({k: v for k, v in snapshot.items() if k != 'snapshot_hash'}) == EXPECTED
    assert snapshot['snapshot_hash'] == source['manifest_hash'] == EXPECTED
    frozen = {d['document_id']: d['revision_id'] for d in snapshot['documents']}
    with (BASE / 'pilot24_manifest.csv').open(encoding='utf-8-sig', newline='') as f:
        manifest = list(csv.DictReader(f))
    templates = [json.loads(s) for s in (BASE / 'gold_annotation_template.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(manifest) == len(templates) == 24
    assert Counter(m['split'] for m in manifest) == {'DEV': 12, 'CALIBRATION': 6, 'HOLDOUT': 6}
    for field in ('document_code', 'document_id', 'revision_id', 'openalex_id'):
        assert len({m[field] for m in manifest}) == 24
    docs = {d['id']: d for d in source['documents']}
    revisions = {r['id']: r for r in source['revisions']}
    out, chunk_ids = [], set()
    for m in manifest:
        UUID(m['document_id']); UUID(m['revision_id'])
        template = next(t for t in templates if t['document_code'] == m['document_code'])
        for field in ('document_id', 'revision_id', 'split'):
            assert template[field] == m[field]
        d, r = docs[m['document_id']], revisions[m['revision_id']]
        assert frozen[d['id']] == r['id'] and r['document_id'] == d['id']
        assert d['source'] == 'openalex' and d['external_id'] == m['openalex_id']
        assert stable(r['normalized_json']) == r['content_hash'], 'Revision content mismatch'
        chunks = sorted((c for c in source['chunks'] if c['revision_id'] == r['id']),
                        key=lambda c: (c['section'], c['ordinal'], c['id']))
        assert chunks
        converted = []
        for c in chunks:
            UUID(c['id'])
            assert c['id'] not in chunk_ids
            chunk_ids.add(c['id'])
            assert c['text'] and sha(c['text'].encode('utf-8')) == c['hash']
            section = next(s for s in r['normalized_json']['sections'] if s['name'] == c['section'])
            assert section['text'][c['section_start']:c['section_end']] == c['text']
            converted.append(dict(chunk_id=c['id'], section=c['section'], ordinal=c['ordinal'],
                                  section_start=c['section_start'], section_end=c['section_end'],
                                  language=c['language'], stored_chunk_hash=c['hash'],
                                  text_sha256=sha(c['text'].encode('utf-8')), text=c['text']))
        # Ensure the available abstract is fully represented, including gaps between chunks.
        for section in r['normalized_json']['sections']:
            covered = set()
            for c in chunks:
                if c['section'] == section['name']:
                    covered.update(range(c['section_start'], c['section_end']))
            assert all(i in covered or ch.isspace() for i, ch in enumerate(section['text']))
        out.append(dict(**m, source=d['source'], title=d['title'],
                        revision_content_hash=r['content_hash'], chunks=converted))
    target = BASE / 'pilot24_sources.jsonl'
    save_new(target, ''.join(json.dumps(d, ensure_ascii=False) + '\n' for d in out))
    report = dict(status='PASS', mode='VERIFIED_ARCHIVED_READ_ONLY_EXPORT',
                  source_archive=str(archive.relative_to(ROOT)), archive_sha256=archive_hash,
                  archive_exported_at_utc=source['exported_at_utc'],
                  snapshot_file=str(snap_path.relative_to(ROOT)),
                  snapshot_hash_expected=EXPECTED, snapshot_hash_recomputed=EXPECTED,
                  snapshot_verification='Local snapshot independently rehashed; original file unchanged.',
                  live_database_verification='NOT_PERFORMED: Docker Desktop engine pipe missing; Docker service stopped.',
                  documents=len(out), chunks=len(chunk_ids), split_counts=dict(Counter(m['split'] for m in manifest)),
                  manifest_ids='PASS', template_ids='PASS', openalex_ids='PASS',
                  revision_hashes='PASS', chunk_hashes='PASS', original_section_spans='PASS',
                  abstract_nonwhitespace_coverage='PASS',
                  source_output_sha256=sha(target.read_bytes()),
                  limitations=['No current PostgreSQL comparison; this is the archived 2026-10-02 state.',
                               'Snapshot integrity is not human validation of annotation semantics.',
                               'Publication/author/family leakage review remains pending before HOLDOUT closure.'])
    save_new(BASE / 'annotations/reports/source_integrity.json', json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    for name in ('drafts', 'reviews', 'gold', 'reports'):
        (BASE / 'annotations' / name).mkdir(parents=True, exist_ok=True)
    print(json.dumps({k: report[k] for k in ('status', 'mode', 'documents', 'chunks', 'split_counts')}))


if __name__ == '__main__':
    main()
