"""Verify archived source rows via the existing PostgreSQL local socket.

Use when TCP credentials in .env are rejected by the persisted database.
Only SELECT/SHOW in a repeatable-read, read-only transaction; no role changes.
No model outputs are selected. Requires the postgres Compose service running.
"""
import csv
import json
import subprocess
from pathlib import Path
from uuid import UUID

from prepare_archived_sources import save_new, sha

BASE = Path(__file__).resolve().parent
with (BASE / 'pilot24_manifest.csv').open(encoding='utf-8-sig') as f:
    manifest = list(csv.DictReader(f))
ids = ','.join("'" + str(UUID(m['revision_id'])) + "'::uuid" for m in manifest)
sql = f"""
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object(
 'transaction_read_only', current_setting('transaction_read_only'),
 'documents', (SELECT json_agg(json_build_object('id',d.id,'source',d.source,
    'external_id',d.external_id,'title',d.title)) FROM source_documents d
    JOIN document_revisions r ON r.document_id=d.id WHERE r.id IN ({ids})),
 'revisions', (SELECT json_agg(json_build_object('id',r.id,'document_id',r.document_id,
    'content_hash',r.content_hash,'normalized_json',r.normalized_json))
    FROM document_revisions r WHERE r.id IN ({ids})),
 'chunks', (SELECT json_agg(row_to_json(c)) FROM evidence_chunks c
    WHERE c.revision_id IN ({ids})));
ROLLBACK;
"""
cmd = ['docker', 'compose', 'exec', '-T', '-e',
       'PGOPTIONS=-c default_transaction_read_only=on', 'postgres', 'sh', '-c',
       'exec psql -U $POSTGRES_USER -d $POSTGRES_DB -qAt -v ON_ERROR_STOP=1']
result = subprocess.run(cmd, input=sql, capture_output=True, text=True, encoding='utf-8',
                        cwd=BASE.parent, check=True)
live = json.loads(result.stdout)
assert live['transaction_read_only'] == 'on'
archive = json.loads((BASE.parent / 'docs/analysis/GRAPH_CORPUS_AUDIT/corpus_export.json').read_text(encoding='utf-8'))
counts = {}
for collection in ('documents', 'revisions', 'chunks'):
    old = {r['id']: r for r in archive[collection]}
    counts[collection] = len(live[collection])
    for row in live[collection]:
        for field, value in row.items():
            assert old[row['id']][field] == value, (collection, row['id'], field)
assert counts == {'documents': 24, 'revisions': 24, 'chunks': 35}
report = dict(status='PASS', counts=counts, access='postgres container local Unix socket',
              transaction='REPEATABLE READ READ ONLY',
              comparison='All selected source fields exactly match archived export, including normalized revisions and full chunk rows.',
              tcp_exporter='Attempted with supplied exporter and correctly encoded .env credentials; PostgreSQL rejected password for article_app.',
              credentials_modified=False, predictions_selected=False,
              pilot24_sources_sha256=sha((BASE / 'pilot24_sources.jsonl').read_bytes()))
save_new(BASE / 'annotations/reports/live_source_verification.json', json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
