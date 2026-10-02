import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../../api/client';
import { readEvents } from '../../api/sse';
import type { Run } from '../../api/types';
import { applyEvent, initialState, terminal, type RunState } from './runState';

export type Connection = 'connecting' | 'live' | 'reconnecting' | 'offline' | 'closed';
export function useRun(run: Run | null) {
  const [state, setState] = useState<RunState | null>(run ? initialState(run) : null);
  const [connection, setConnection] = useState<Connection>('closed');
  const current = useRef<RunState | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    if (!run) {
      current.current = null;
      setState(null);
      setConnection('closed');
      return;
    }
    current.current = initialState(run);
    setState(current.current);
    if (terminal(run)) {
      setConnection('closed');
      return;
    }
    const update = (value: RunState) => {
      current.current = value;
      setState(value);
    };
    const recover = async (reset = false) => {
      const snapshot = await api.run(run.id);
      if (controller.signal.aborted) return;
      if (reset || terminal(snapshot) || !current.current) update(initialState(snapshot));
      else
        update({
          ...current.current,
          run: { ...snapshot, public_analysis: current.current.run.public_analysis },
        });
    };
    const sleep = (ms: number) =>
      new Promise<void>((resolve) => {
        const finish = () => {
          clearTimeout(retryTimer);
          controller.signal.removeEventListener('abort', finish);
          resolve();
        };
        retryTimer = setTimeout(finish, ms);
        controller.signal.addEventListener('abort', finish, { once: true });
      });
    async function connect() {
      let attempts = 0;
      while (!controller.signal.aborted && current.current && !terminal(current.current.run)) {
        setConnection(attempts ? 'reconnecting' : 'connecting');
        let retryAfter = 0;
        try {
          await readEvents(
            run!.id,
            current.current.seq,
            controller.signal,
            ({ type, envelope }) => {
              if (controller.signal.aborted || !current.current) return;
              const next = applyEvent(current.current, type, envelope);
              if (next.mismatch) throw new Error('STREAM_MISMATCH');
              update(next);
              setConnection('live');
              attempts = 0;
            },
          );
          if (!controller.signal.aborted) await recover();
        } catch (error) {
          if (controller.signal.aborted) return;
          if (error instanceof ApiError && error.status === 401) {
            window.dispatchEvent(new Event('session-expired'));
            return;
          }
          if (error instanceof ApiError && error.status === 404) {
            setConnection('offline');
            return;
          }
          retryAfter = error instanceof ApiError ? error.retryAfter * 1000 : 0;
          try {
            await recover(error instanceof Error && error.message === 'STREAM_MISMATCH');
          } catch {
            /* Повторяем после восстановления сети. */
          }
        }
        if (current.current && terminal(current.current.run)) break;
        attempts += 1;
        setConnection('reconnecting');
        await sleep(Math.max(retryAfter, Math.min(1000 * 2 ** Math.min(attempts - 1, 4), 15000)));
      }
      if (!controller.signal.aborted) setConnection('closed');
    }
    void connect();
    return () => {
      controller.abort();
      clearTimeout(retryTimer);
    };
  }, [run]);
  return { state, connection };
}
