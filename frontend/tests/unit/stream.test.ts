import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { Envelope, Run } from '../../src/api/types.ts';
import { applyEvent, hash, initialState } from '../../src/features/chat/runState.ts';
import { parseFrame, readEvents } from '../../src/api/sse.ts';

const run: Run = {
  id: 'run-a',
  status: 'running',
  stage: 'analyzing',
  progress: {},
  idea_version_id: null,
  source_run_id: null,
  outcome: null,
  answer: null,
  public_analysis: null,
  answer_presentation: null,
  sources: [],
  coverage: { sources: [], channels: [], partial: false, historical: false },
  graph_url: null,
  created_at: '2026-10-02T10:00:00Z',
  completed_at: null,
  error_code: null,
};
const event = (seq: number, payload: Record<string, unknown>, id = run.id): Envelope => ({
  seq,
  payload,
  run_id: id,
  at: run.created_at,
});
const verified = () =>
  applyEvent(initialState(run), 'verification', event(1, { phase: 'completed', scope: 'result' }));
const start = (text: string, chunks = 1) =>
  applyEvent(
    verified(),
    'answer_started',
    event(2, {
      presentation_id: hash('test-v1' + text),
      renderer_version: 'test-v1',
      text_sha256: hash(text),
      chunk_count: chunks,
    }),
  );

test('dedupe by run/seq and authoritative completed replaces partial answer', () => {
  let state = start('hello');
  const frame = event(3, { presentation_id: hash('test-v1hello'), chunk_index: 0, text: 'hello' });
  state = applyEvent(state, 'answer_delta', frame);
  assert.equal(applyEvent(state, 'answer_delta', frame), state);
  assert.equal(state.text, 'hello');
  const completed = { ...run, status: 'completed', answer_presentation: { text: 'authoritative' } };
  const final = applyEvent(state, 'completed', event(4, { run: completed }));
  assert.equal(final.text, 'authoritative');
  assert.equal(final.run.status, 'completed');
});
test('gaps, wrong run, wrong index and hash are rejected', () => {
  const state = start('correct');
  for (const [seq, payload, id] of [
    [4, { presentation_id: hash('test-v1correct'), chunk_index: 0, text: 'correct' }, run.id],
    [3, { presentation_id: hash('test-v1correct'), chunk_index: 1, text: 'correct' }, run.id],
    [3, { presentation_id: hash('test-v1correct'), chunk_index: 0, text: 'tampered' }, run.id],
    [3, { presentation_id: hash('test-v1correct'), chunk_index: 0, text: 'correct' }, 'other-run'],
  ] as const)
    assert.equal(applyEvent(state, 'answer_delta', event(seq, payload, id)).mismatch, true);
});
test('summary/draft cannot appear before result verification', () => {
  const state = initialState(run);
  assert.equal(
    applyEvent(
      state,
      'analysis_summary',
      event(1, { public_analysis: { items: ['RAW_REASONING_SENTINEL'] } }),
    ).mismatch,
    true,
  );
  assert.equal(
    applyEvent(state, 'raw_reasoning', event(1, { text: 'RAW_REASONING_SENTINEL' })).mismatch,
    true,
  );
  assert.equal(state.text, '');
});
test('reset replaces text and summary; stale reset is ignored', () => {
  const state = applyEvent(
    start('hello'),
    'answer_delta',
    event(3, { presentation_id: hash('test-v1hello'), chunk_index: 0, text: 'hello' }),
  );
  const replaced = applyEvent(state, 'run_snapshot', event(7, { run, reset: true, high_water: 7 }));
  assert.equal(replaced.text, '');
  assert.equal(replaced.run.public_analysis, null);
  assert.equal(replaced.seq, 7);
  assert.equal(
    applyEvent(replaced, 'run_snapshot', event(6, { run, reset: true, high_water: 6 })),
    replaced,
  );
});
test('requeue resets earlier attempt counts and presentation', () => {
  const result = applyEvent(
    verified(),
    'run_requeued',
    event(2, {
      progress: { schema_version: 1, attempt: 2, stage: 'planning', phase: 'waiting', counts: {} },
    }),
  );
  assert.equal(result.verified, false);
  assert.deepEqual(result.run.progress.counts, {});
});
test('parser handles heartbeat and multiline data, checks SSE id', () => {
  assert.equal(parseFrame(': heartbeat'), null);
  const frame = parseFrame(
    'id: 1\nevent: planning\ndata: {"run_id":"run-a","seq":1,\ndata: "at":"now","payload":{}}',
  );
  assert.equal(frame?.envelope.seq, 1);
  assert.throws(() => parseFrame('id: 2\ndata: {"run_id":"run-a","seq":1,"payload":{}}'));
});
test('network parser survives split UTF-8 and split CRLF', async () => {
  const original = globalThis.fetch;
  const bytes = new TextEncoder().encode(
    'id: 1\r\nevent: planning\r\ndata: {"run_id":"run-a","seq":1,"at":"now","payload":{"text":"Привет 🙂"}}\r\n\r\n',
  );
  globalThis.fetch = async () =>
    new Response(
      new ReadableStream({
        start(controller) {
          for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
          controller.close();
        },
      }),
    );
  try {
    const frames: string[] = [];
    await readEvents('run-a', 0, new AbortController().signal, (frame) =>
      frames.push(String(frame.envelope.payload.text)),
    );
    assert.deepEqual(frames, ['Привет 🙂']);
  } finally {
    globalThis.fetch = original;
  }
});
