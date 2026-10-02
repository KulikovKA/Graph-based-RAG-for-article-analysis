import { sha256 } from '@noble/hashes/sha2.js';
import { bytesToHex } from '@noble/hashes/utils.js';
import type {
  Envelope,
  Presentation,
  Progress,
  PublicAnalysis,
  Run,
  Source,
  Coverage,
} from '../../api/types';

export const terminal = (run: Run) => ['completed', 'failed', 'cancelled'].includes(run.status);
export const hash = (text: string) => bytesToHex(sha256(new TextEncoder().encode(text)));
type Header = Omit<Presentation, 'text' | 'schema_version'>;
export interface RunState {
  run: Run;
  seq: number | null;
  chunks: string[];
  header: Header | null;
  text: string;
  verified: boolean;
  mismatch: boolean;
}
export function initialState(run: Run): RunState {
  return {
    run,
    seq: null,
    chunks: [],
    header: null,
    text: run.answer_presentation?.text ?? '',
    verified: run.status === 'completed',
    mismatch: false,
  };
}

export function applyEvent(state: RunState, type: string, event: Envelope): RunState {
  if (event.run_id !== state.run.id) return { ...state, mismatch: true };
  if (type !== 'run_snapshot' && state.seq !== null && event.seq <= state.seq) return state;
  const p = event.payload;
  if (type === 'run_snapshot') {
    if (state.seq !== null && event.seq < state.seq) return state;
    if (
      p.reset !== true ||
      p.high_water !== event.seq ||
      !(p.run as Run)?.id ||
      (p.run as Run).id !== state.run.id
    )
      return { ...state, mismatch: true };
    return { ...initialState(p.run as Run), seq: event.seq };
  }
  if (state.seq !== null && event.seq !== state.seq + 1) return { ...state, mismatch: true };
  let next: RunState = { ...state, seq: event.seq };
  if (['completed', 'failed', 'cancelled'].includes(type)) {
    const run = p.run as Run;
    if (!run || run.id !== state.run.id || run.status !== type) return { ...state, mismatch: true };
    return { ...initialState(run), seq: event.seq };
  }
  if (terminal(state.run)) return next;
  if (
    [
      'run_started',
      'planning',
      'idea_updated',
      'retrieving',
      'reranking',
      'analyzing',
      'run_requeued',
    ].includes(type)
  ) {
    const progress = p.progress as Progress;
    if (!progress || typeof progress.stage !== 'string' || !progress.counts)
      return { ...state, mismatch: true };
    next.run = {
      ...state.run,
      progress,
      stage: progress.stage,
      idea_version_id:
        typeof p.idea_version_id === 'string' ? p.idea_version_id : state.run.idea_version_id,
    };
    if (type === 'run_requeued')
      next = {
        ...next,
        chunks: [],
        header: null,
        text: '',
        verified: false,
        run: { ...next.run, public_analysis: null, answer_presentation: null },
      };
  } else if (type === 'sources_ready') {
    next.run = { ...state.run, sources: p.sources as Source[], coverage: p.coverage as Coverage };
  } else if (type === 'verification') {
    next.verified = p.phase === 'completed' && p.scope === 'result';
    next.run = { ...state.run, stage: 'verification' };
  } else if (type === 'analysis_summary') {
    if (!state.verified) return { ...state, mismatch: true };
    next.run = { ...state.run, public_analysis: p.public_analysis as PublicAnalysis };
  } else if (type === 'answer_started') {
    if (
      !state.verified ||
      typeof p.presentation_id !== 'string' ||
      typeof p.text_sha256 !== 'string' ||
      !Number.isInteger(p.chunk_count) ||
      Number(p.chunk_count) < 1 ||
      Number(p.chunk_count) > 128
    )
      return { ...state, mismatch: true };
    next = { ...next, header: p as unknown as Header, chunks: [], text: '' };
  } else if (type === 'answer_delta') {
    if (
      !state.header ||
      p.presentation_id !== state.header.presentation_id ||
      p.chunk_index !== state.chunks.length ||
      typeof p.text !== 'string' ||
      Array.from(p.text).length > 1024 ||
      state.chunks.length >= state.header.chunk_count
    )
      return { ...state, mismatch: true };
    const chunks = [...state.chunks, p.text];
    const text = chunks.join('');
    if (new TextEncoder().encode(text).length > 65536) return { ...state, mismatch: true };
    if (
      chunks.length === state.header.chunk_count &&
      (hash(text) !== state.header.text_sha256 ||
        hash(state.header.renderer_version + text) !== state.header.presentation_id)
    )
      return { ...state, mismatch: true };
    next = { ...next, chunks, text };
  } else return { ...state, mismatch: true };
  return next;
}
