import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, errorMessage } from '../../api/client';
import type { Conversation, Run, RunHistoryItem } from '../../api/types';
import { initialState } from './runState';
import { RunView } from './RunView';

export function ConversationTools({ conversation, onRenamed, onDeleted, onCitation }: {
  conversation: Conversation;
  onRenamed: (value: Conversation) => void;
  onDeleted: () => void;
  onCitation: (run: Run, id: string) => void;
}) {
  const [title, setTitle] = useState(conversation.title ?? '');
  const [editing, setEditing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [items, setItems] = useState<RunHistoryItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [run, setRun] = useState<Run | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const live = useRef(true);
  useEffect(() => { live.current = true; return () => { live.current = false; }; }, []);
  async function rename(event: FormEvent) {
    event.preventDefault();
    if (!title.trim() || title.length > 160) { setError('Название должно содержать от 1 до 160 символов.'); return; }
    setBusy(true); setError('');
    try {
      const value = await api.renameConversation(conversation.id, title.trim());
      if (live.current) { onRenamed(value); setEditing(false); }
    } catch (cause) { if (live.current) setError(errorMessage(cause)); }
    finally { if (live.current) setBusy(false); }
  }
  async function resetTitle() {
    setBusy(true); setError('');
    try {
      const value = await api.renameConversation(conversation.id, null);
      if (live.current) { onRenamed(value); setTitle(''); setEditing(false); }
    } catch (cause) { if (live.current) setError(errorMessage(cause)); }
    finally { if (live.current) setBusy(false); }
  }
  async function remove() {
    if (!window.confirm('Удалить диалог и все его исследования? Это действие нельзя отменить.')) return;
    setBusy(true); setError('');
    try { await api.deleteConversation(conversation.id); if (live.current) onDeleted(); }
    catch (cause) { if (live.current) setError(errorMessage(cause)); }
    finally { if (live.current) setBusy(false); }
  }
  async function history(next?: string) {
    setBusy(true); setError('');
    try {
      const page = await api.conversationRuns(conversation.id, next);
      if (live.current) { setItems((old) => next ? [...old, ...page.items] : page.items); setCursor(page.next_cursor); setLoaded(true); }
    } catch (cause) { if (live.current) setError(errorMessage(cause)); }
    finally { if (live.current) setBusy(false); }
  }
  async function openRun(id: string) {
    setBusy(true); setError(''); setRun(null);
    try { const value = await api.run(id); if (live.current) setRun(value); }
    catch (cause) { if (live.current) setError(errorMessage(cause)); }
    finally { if (live.current) setBusy(false); }
  }
  return <section className="conversation-tools" aria-label="Управление диалогом">
    <div className="conversation-actions">
      <button className="text-button" disabled={busy} onClick={() => setEditing((value) => !value)}>Переименовать</button>
      <button className="text-button" disabled={busy} onClick={() => void remove()}>Удалить диалог</button>
      <button className="text-button" disabled={busy} aria-expanded={showHistory} onClick={() => { setShowHistory(!showHistory); if (!showHistory && !loaded) void history(); }}>История исследований</button>
    </div>
    {editing && <form onSubmit={(event) => void rename(event)} className="conversation-rename">
      <label>Название диалога <input value={title} maxLength={160} onChange={(event) => setTitle(event.target.value)} /></label>
      <button disabled={busy}>Сохранить</button>
      <button type="button" disabled={busy} onClick={() => void resetTitle()}>Сбросить название</button>
    </form>}
    {error && <p role="alert" className="notice error">{error}</p>}
    {showHistory && <div className="conversation-history">
      {loaded && !items.length && <p>Исследований пока нет.</p>}
      {items.map((item) => <div key={item.id} className="history-item">
        <button className="text-button" disabled={busy} onClick={() => void openRun(item.id)}>{new Date(item.created_at).toLocaleString('ru-RU')} · {item.status}</button>
        <small>Результат: {item.outcome ?? '—'} · Завершено: {item.completed_at ? new Date(item.completed_at).toLocaleString('ru-RU') : '—'} · Версия идеи: {item.idea_version_id ?? '—'} · Индекс: {item.index_generation_id ?? '—'}</small>
      </div>)}
      {cursor && <button className="text-button" disabled={busy} onClick={() => void history(cursor)}>Ещё исследования</button>}
      {run && <RunView state={initialState(run)} connection="closed" onCitation={(id) => onCitation(run, id)} />}
    </div>}
  </section>;
}
