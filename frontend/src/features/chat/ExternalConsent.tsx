import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError, errorMessage } from '../../api/client';

function readGrant(value: { notice_version: string; granted: boolean }): boolean {
  if (value.notice_version !== 'groq_context_v1' || typeof value.granted !== 'boolean') {
    throw new ApiError(502, 'INVALID_CONSENT');
  }
  return value.granted;
}

export function ExternalConsent({ runId }: { runId: string }) {
  const [granted, setGranted] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const controller = useRef<AbortController | null>(null);

  const load = useCallback(async (signal: AbortSignal) => {
    setBusy(true); setError('');
    try {
      const value = readGrant(await api.externalConsent(runId, signal));
      if (!signal.aborted) setGranted(value);
    } catch (cause) {
      if (!signal.aborted) { setGranted(null); setError(errorMessage(cause)); }
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  }, [runId]);

  useEffect(() => {
    const current = new AbortController();
    controller.current = current;
    void load(current.signal);
    return () => { current.abort(); };
  }, [load]);

  async function update(revoke: boolean) {
    const signal = controller.current?.signal;
    if (!signal || signal.aborted) return;
    setBusy(true); setError('');
    try {
      if (revoke) {
        await api.revokeExternalConsent(runId, signal);
        if (!signal.aborted) setGranted(false);
      } else {
        const value = readGrant(await api.grantExternalConsent(runId, signal));
        if (!signal.aborted) setGranted(value);
      }
    } catch (cause) {
      if (!signal.aborted) { setGranted(null); setError(errorMessage(cause)); }
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  }

  return <section className="external-consent" aria-label="Согласие на внешнюю обработку">
    <h2>Внешняя обработка этого исследования</h2>
    <p>Выбранное исследование: {runId}</p>
    <p>При подключении внешней генерации минимизированный контекст исследования может передаваться провайдеру Groq. Разрешение действует только для выбранного исследования и его можно отозвать.</p>
    <p>Рабочая передача данных пока не включена. Сохранение разрешения само по себе не запускает передачу.</p>
    <p role="status">{busy ? 'Проверяем состояние…' : granted === null ? 'Состояние разрешения неизвестно.' : granted ? 'Разрешение сохранено.' : 'Разрешение не предоставлено.'}</p>
    {error && <p className="notice error" role="alert">{error}</p>}
    {granted !== null && <button type="button" disabled={busy} onClick={() => void update(granted)}>{granted ? 'Отозвать разрешение' : 'Разрешить внешнюю обработку'}</button>}
    {!busy && granted === null && <button type="button" onClick={() => { if (controller.current) void load(controller.current.signal); }}>Повторить проверку</button>}
  </section>;
}
