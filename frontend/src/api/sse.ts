import type { Envelope } from './types';
import { ApiError } from './client.ts';

export interface Frame {
  type: string;
  envelope: Envelope;
}

export function parseFrame(raw: string): Frame | null {
  if (raw.length > 262144) throw new Error('EVENT_TOO_LARGE');
  let type = 'message',
    id = '';
  const data: string[] = [];
  for (const line of raw.split('\n')) {
    if (line.startsWith(':')) continue;
    const colon = line.indexOf(':');
    const key = colon < 0 ? line : line.slice(0, colon);
    const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '');
    if (key === 'event') type = value;
    if (key === 'id') id = value;
    if (key === 'data') data.push(value);
  }
  if (!data.length) return null;
  const envelope = JSON.parse(data.join('\n')) as Envelope;
  if (
    !envelope ||
    !Number.isSafeInteger(envelope.seq) ||
    envelope.seq < 0 ||
    String(envelope.seq) !== id ||
    typeof envelope.run_id !== 'string' ||
    typeof envelope.payload !== 'object' ||
    !envelope.payload
  )
    throw new Error('INVALID_EVENT');
  return { type, envelope };
}

export async function readEvents(
  run: string,
  seq: number | null,
  signal: AbortSignal,
  onFrame: (frame: Frame) => void,
): Promise<void> {
  const headers = new Headers({ Accept: 'text/event-stream' });
  if (seq !== null) headers.set('Last-Event-ID', String(seq));
  const response = await fetch(`/api/v1/runs/${encodeURIComponent(run)}/events`, {
    credentials: 'same-origin',
    headers,
    signal,
    cache: 'no-store',
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      body.error?.code ?? 'STREAM_UNAVAILABLE',
      Number(response.headers.get('Retry-After') ?? 0),
    );
  }
  if (!response.body) throw new Error('MISSING_STREAM');
  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let buffer = '';
  try {
    while (true) {
      let timedOut = false;
      const timer = setTimeout(() => {
        timedOut = true;
        void reader.cancel();
      }, 35000);
      let result: ReadableStreamReadResult<Uint8Array>;
      try {
        result = await reader.read();
      } finally {
        clearTimeout(timer);
      }
      const { value, done } = result;
      if (timedOut) throw new Error('STREAM_IDLE');
      buffer += decoder.decode(value, { stream: !done });
      // CRLF может быть разрезан между network chunks; нормализация после накопления.
      buffer = buffer.replace(/\r\n/g, '\n');
      let boundary: number;
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const frame = parseFrame(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        if (frame) onFrame(frame);
      }
      if (buffer.length > 262144) throw new Error('EVENT_TOO_LARGE');
      if (done) {
        if (buffer.trim()) throw new Error('TRUNCATED_EVENT');
        return;
      }
    }
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}
