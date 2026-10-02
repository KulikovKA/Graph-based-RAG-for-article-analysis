import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, errorMessage, randomKey, setSession } from './api/client';
import type {
  Conversation,
  ConversationDetail,
  Evidence,
  Message,
  MessageInput,
  Run,
  Session,
  Source,
} from './api/types';
import { Mark, SendIcon } from './components/Icons';
import { RunView } from './features/chat/RunView';
import { initialState, terminal } from './features/chat/runState';
import { useRun } from './features/chat/useRun';
import { SourceCards } from './features/sources/SourceCards';

function Login({ onLogin }: { onLogin: (value: Session) => void }) {
  const [email, setEmail] = useState(''),
    [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const value = await api.login(email, password);
      setPassword('');
      onLogin(value);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <div className="login-brand">
        <Mark />
        <span>
          Контекст<span className="brand-sub">Анализ публикаций</span>
        </span>
      </div>
      <section className="login-card">
        <span className="eyebrow">Рабочее пространство</span>
        <h1>
          От идеи —<br />к первоисточникам.
        </h1>
        <p>
          Сравнивайте технические признаки с публикациями и патентами. Проверяйте каждый вывод по
          цитате.
        </p>
        <form onSubmit={submit}>
          <label>
            Электронная почта
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label>
            Пароль
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && (
            <p className="notice error" role="alert">
              {error}
            </p>
          )}
          <button className="primary" disabled={busy}>
            {busy ? 'Входим…' : 'Войти в пространство'}
            <span>→</span>
          </button>
        </form>
        <p className="login-footnote">Аккаунт предоставляет оператор вашего проекта.</p>
      </section>
      <span className="login-caption">Идеи · Источники · Проверяемые выводы</span>
    </main>
  );
}

export default function App() {
  const [session, sessionValue] = useState<Session | null>(null),
    [booting, setBooting] = useState(true);
  const [conversations, setConversations] = useState<Conversation[]>([]),
    [cursor, setCursor] = useState<string | null>(null);
  const [detail, setDetail] = useState<ConversationDetail | null>(null),
    [selected, setSelected] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]),
    [runs, setRuns] = useState<Record<string, Run>>({});
  const [initialRun, setInitialRun] = useState<Run | null>(null),
    [sourceRun, setSourceRun] = useState<Run | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({}),
    [followup, setFollowup] = useState<{ run: string; title: string } | null>(null);
  const [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(false);
  const [navOpen, setNavOpen] = useState(false),
    [activeEvidence, setActiveEvidence] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null),
    [evidenceLoading, setEvidenceLoading] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);
  const { state, connection } = useRun(initialRun);
  const composer = useRef<HTMLTextAreaElement>(null);
  const generation = useRef(0),
    evidenceRequest = useRef(0);
  const pending = useRef<{ body: string; key: string } | null>(null);
  const draftKey = selected ?? 'new';
  const draft = drafts[draftKey] ?? '';
  const currentRun = state?.run ?? initialRun;
  const active = currentRun && !terminal(currentRun);

  const authenticate = useCallback((value: Session | null) => {
    setSession(value);
    sessionValue(value);
    setBooting(false);
    if (!value) {
      generation.current++;
      evidenceRequest.current++;
      setConversations([]);
      setMessages([]);
      setRuns({});
      setInitialRun(null);
      setSourceRun(null);
      setSelected(null);
      setDetail(null);
      setDrafts({});
      setFollowup(null);
      setActiveEvidence(null);
      setEvidence(null);
      setBusy(false);
      setLoading(false);
      pending.current = null;
    }
  }, []);
  useEffect(() => {
    let live = true;
    api
      .session()
      .then((value) => {
        if (live) authenticate(value);
      })
      .catch(() => {
        if (live) authenticate(null);
      });
    const expired = () => authenticate(null);
    window.addEventListener('session-expired', expired);
    return () => {
      live = false;
      window.removeEventListener('session-expired', expired);
    };
  }, [authenticate]);
  const refreshList = useCallback(async () => {
    const gen = generation.current;
    const page = await api.conversations();
    if (gen === generation.current) {
      setConversations(page.items);
      setCursor(page.next_cursor);
    }
  }, []);
  useEffect(() => {
    if (session) void refreshList().catch((cause) => setError(errorMessage(cause)));
  }, [session, refreshList]);
  useEffect(() => {
    if (!state) return;
    if (state.run.status === 'completed' && selected) {
      const id = selected;
      setRuns((value) => ({ ...value, [state.run.id]: state.run }));
      const gen = generation.current;
      void api
        .conversation(id)
        .then((value) => {
          if (generation.current === gen) setDetail(value);
        })
        .catch(() => undefined);
    }
  }, [state?.run, selected]);

  async function selectConversation(id: string | null) {
    const gen = ++generation.current;
    evidenceRequest.current++;
    setSelected(id);
    setDetail(null);
    setMessages([]);
    setRuns({});
    setInitialRun(null);
    setSourceRun(null);
    setActiveEvidence(null);
    setEvidence(null);
    setFollowup(null);
    setError('');
    setNavOpen(false);
    pending.current = null;
    if (!id) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const value = await api.conversation(id);
      let page = await api.messages(id),
        history = page.items;
      while (page.next_cursor) {
        page = await api.messages(id, page.next_cursor);
        history = [...history, ...page.items];
      }
      const saved: Record<string, Run> = {};
      // История загружается последовательно, не создавая burst по user rate limit.
      for (const runId of value.last_runs) saved[runId] = await api.run(runId);
      if (gen !== generation.current) return;
      setDetail(value);
      setMessages(history);
      setRuns(saved);
      const latest = value.last_runs[0] ? saved[value.last_runs[0]] : null;
      setInitialRun(latest);
      setSourceRun(latest);
    } catch (cause) {
      if (gen === generation.current) setError(errorMessage(cause));
    } finally {
      if (gen === generation.current) setLoading(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft.trim() || busy || active || loading) return;
    if (selected && !detail) {
      setError('Диалог не загружен. Откройте его повторно в списке.');
      return;
    }
    if (new TextEncoder().encode(draft).length > 8192) {
      setError('Текст слишком длинный. Максимум — 8 КиБ.');
      return;
    }
    setBusy(true);
    setError('');
    const gen = generation.current;
    try {
      let conversation = detail;
      if (!conversation) {
        const created = await api.create(draft.trim().slice(0, 70));
        conversation = { ...created, idea: null, last_runs: [] };
        if (gen !== generation.current) return;
        setDetail(conversation);
        setSelected(conversation.id);
        setDrafts((value) => ({ ...value, [conversation!.id]: draft }));
        await refreshList();
      }
      const input: MessageInput = {
        content: draft,
        expected_idea_version: conversation.idea?.version_no ?? 0,
        analyze: true,
        ...(followup ? { source_run_id: followup.run } : {}),
      };
      const body = JSON.stringify({ conversation: conversation.id, input });
      if (!pending.current || pending.current.body !== body)
        pending.current = { body, key: randomKey() };
      const accepted = await api.send(conversation.id, input, pending.current.key);
      if (gen !== generation.current) return;
      const run = await api.run(accepted.run_id);
      setMessages((value) =>
        value.some((x) => x.id === accepted.message_id)
          ? value
          : [
              ...value,
              {
                id: accepted.message_id,
                role: 'user',
                content: draft,
                run_id: accepted.run_id,
                created_at: run.created_at,
              },
            ],
      );
      setInitialRun(run);
      setSourceRun(run);
      setRuns((value) => ({ ...value, [run.id]: run }));
      setDrafts((value) => ({ ...value, [conversation.id]: '', new: '' }));
      setFollowup(null);
      pending.current = null;
      setActiveEvidence(null);
      setEvidence(null);
      void refreshList();
    } catch (cause) {
      if (gen !== generation.current) return;
      setError(errorMessage(cause));
      if (cause instanceof ApiError && cause.code === 'VERSION_CONFLICT' && selected) {
        setDetail(await api.conversation(selected));
        pending.current = null;
      }
    } finally {
      if (gen === generation.current) setBusy(false);
    }
  }

  async function citation(run: Run, evidenceId: string) {
    const source = run.sources.find((x) => x.evidence_ids.includes(evidenceId));
    if (!source) {
      setError('Цитата отсутствует в источниках этого анализа.');
      return;
    }
    const request = ++evidenceRequest.current;
    setSourceRun(run);
    setActiveEvidence(evidenceId);
    setEvidence(null);
    setEvidenceLoading(true);
    try {
      const value = await api.evidence(run.id, evidenceId);
      if (request === evidenceRequest.current) setEvidence(value);
    } catch (cause) {
      if (request === evidenceRequest.current) setError(errorMessage(cause));
    } finally {
      if (request === evidenceRequest.current) {
        setEvidenceLoading(false);
        requestAnimationFrame(() => {
          const card = document.getElementById(`source-${source.document_id}`);
          card?.scrollIntoView({ behavior: 'auto', block: 'center' });
          card?.focus({ preventScroll: true });
        });
      }
    }
  }
  function explain(source: Source, run: Run) {
    if (run.status !== 'completed') {
      setError('Дождитесь завершения анализа, чтобы обсудить источник.');
      return;
    }
    setFollowup({ run: run.id, title: source.title });
    setDrafts((value) => ({
      ...value,
      [draftKey]: `Объясни, как источник «${source.title}» связан с моей идеей.`,
    }));
    composer.current?.focus();
    composer.current?.scrollIntoView({ block: 'center' });
  }
  async function cancel() {
    if (!currentRun) return;
    const gen = generation.current;
    setCancelBusy(true);
    setError('');
    try {
      const result = await api.cancel(currentRun.id);
      if (result.status === 'completed') {
        const saved = await api.run(currentRun.id);
        if (gen === generation.current) setInitialRun(saved);
      }
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setCancelBusy(false);
    }
  }
  async function showAll() {
    if (!currentRun) return;
    const gen = generation.current;
    try {
      const saved = await api.run(currentRun.id);
      if (gen === generation.current) setInitialRun(saved);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }
  const sources = state && sourceRun?.id === state.run.id ? state.run : sourceRun;
  if (booting)
    return (
      <main className="boot-page">
        <Mark />
        <p>Открываем рабочее пространство…</p>
      </main>
    );
  if (!session) return <Login onLogin={authenticate} />;
  return (
    <div className="workspace">
      <aside className={`sidebar ${navOpen ? 'open' : ''}`} aria-label="Диалоги">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            void selectConversation(null);
          }}
        >
          <Mark />
          <span>
            Контекст<small>Анализ публикаций</small>
          </span>
        </a>
        <button
          className="new-conversation"
          onClick={() => void selectConversation(null)}
          disabled={busy}
        >
          ＋ Новый диалог
        </button>
        <div className="sidebar-label">Ваши исследования</div>
        <nav>
          {conversations.length === 0 && (
            <p className="sidebar-empty">
              Начните с идеи — первый диалог сохранится автоматически.
            </p>
          )}
          {conversations.map((item) => (
            <button
              key={item.id}
              className={`conversation-link ${selected === item.id ? 'active' : ''}`}
              disabled={busy}
              onClick={() => void selectConversation(item.id)}
            >
              <span>{item.title || 'Новый диалог'}</span>
              <small>
                {new Date(item.updated_at).toLocaleDateString('ru-RU', {
                  day: 'numeric',
                  month: 'short',
                })}
              </small>
            </button>
          ))}
          {cursor && (
            <button
              className="text-button"
              onClick={async () => {
                try {
                  const page = await api.conversations(cursor);
                  setConversations((value) => [...value, ...page.items]);
                  setCursor(page.next_cursor);
                } catch (cause) {
                  setError(errorMessage(cause));
                }
              }}
            >
              Ещё диалоги
            </button>
          )}
        </nav>
        <div className="sidebar-footer">
          <span className="avatar">К</span>
          <span>
            Личное пространство<small>История доступна только вам</small>
          </span>
          <button
            title="Выйти"
            aria-label="Выйти"
            onClick={async () => {
              try {
                await api.logout();
                authenticate(null);
              } catch (cause) {
                setError(errorMessage(cause));
              }
            }}
          >
            ↪
          </button>
        </div>
      </aside>
      {navOpen && (
        <button
          className="nav-backdrop"
          aria-label="Закрыть меню"
          onClick={() => setNavOpen(false)}
        />
      )}
      <main className="main-workspace">
        <header className="workspace-header">
          <button
            className="menu-button"
            aria-label="Открыть диалоги"
            onClick={() => setNavOpen(true)}
          >
            ☰
          </button>
          <div>
            <span className="eyebrow">Исследование</span>
            <h1>{detail?.title || 'Новая идея'}</h1>
          </div>
          <span className="version-pill">Версия идеи {detail?.idea?.version_no ?? 0}</span>
        </header>
        <div className={`work-content ${messages.length ? 'has-messages' : ''}`}>
          <section className="chat-panel" aria-label="Чат анализа">
            {loading ? (
              <p className="loading-state" role="status">
                Открываем диалог и сохранённые ответы…
              </p>
            ) : messages.length === 0 ? (
              <div className="welcome">
                <span className="welcome-symbol">✧</span>
                <span className="eyebrow">Начните исследование</span>
                <h2>Какая у вас идея?</h2>
                <p>
                  Опишите устройство, метод или техническую задачу.
                  <br className="desktop-break" /> Мы найдём близкие решения и сравним их признаки.
                </p>
                <div className="welcome-hints">
                  <span>
                    01 <b>Опишите принцип работы</b>
                  </span>
                  <span>
                    02 <b>Укажите отличия</b>
                  </span>
                  <span>
                    03 <b>Проверьте цитаты</b>
                  </span>
                </div>
              </div>
            ) : (
              <div className="transcript">
                {messages
                  .filter((message) => message.role === 'user')
                  .map((message) => {
                    const run = message.run_id
                      ? message.run_id === state?.run.id
                        ? state.run
                        : runs[message.run_id]
                      : null;
                    const runState =
                      run && run.id === state?.run.id ? state : run ? initialState(run) : null;
                    return (
                      <div className="exchange" key={message.id}>
                        <div className="user-message">
                          <span className="eyebrow">Вы</span>
                          <p>{message.content}</p>
                        </div>
                        {runState ? (
                          <RunView
                            key={runState.run.id}
                            state={runState}
                            connection={runState.run.id === state?.run.id ? connection : 'closed'}
                            onCitation={(id) => void citation(runState.run, id)}
                            onCancel={
                              !terminal(runState.run) && !cancelBusy
                                ? () => void cancel()
                                : undefined
                            }
                            onShowAll={() => void showAll()}
                          />
                        ) : (
                          message.run_id && (
                            <button
                              className="text-button"
                              onClick={async () => {
                                try {
                                  const value = await api.run(message.run_id!);
                                  setRuns((prev) => ({ ...prev, [value.id]: value }));
                                } catch (cause) {
                                  setError(errorMessage(cause));
                                }
                              }}
                            >
                              Загрузить сохранённый ответ
                            </button>
                          )
                        )}
                      </div>
                    );
                  })}
              </div>
            )}
            <form className="composer" onSubmit={submit}>
              {followup && (
                <div className="followup-context">
                  <span>Обсуждаем источник: {followup.title}</span>
                  <button
                    type="button"
                    aria-label="Убрать выбранный источник"
                    onClick={() => setFollowup(null)}
                  >
                    ×
                  </button>
                </div>
              )}
              <label className="sr-only" htmlFor="idea">
                Ваша идея или уточнение
              </label>
              <textarea
                ref={composer}
                id="idea"
                rows={3}
                placeholder={
                  messages.length
                    ? 'Уточните идею или задайте вопрос об источниках…'
                    : 'Например: система охлаждения батареи с управлением потоком по температуре отдельных ячеек…'
                }
                value={draft}
                disabled={busy || loading}
                onChange={(e) => setDrafts((value) => ({ ...value, [draftKey]: e.target.value }))}
              />
              <div className="composer-footer">
                <span>
                  {active
                    ? 'Идёт анализ. Новый вопрос можно отправить после завершения.'
                    : 'Подробное описание помогает точнее сравнить признаки.'}
                </span>
                <button
                  className="send-button"
                  type="submit"
                  aria-label="Отправить запрос"
                  disabled={!draft.trim() || busy || active || loading}
                >
                  {busy ? 'Отправляем…' : 'Исследовать'}
                  <SendIcon />
                </button>
              </div>
            </form>
            {error && (
              <p className="notice error" role="alert">
                {error}
                <button
                  className="dismiss"
                  aria-label="Закрыть сообщение"
                  onClick={() => setError('')}
                >
                  ×
                </button>
              </p>
            )}
            <p className="chat-footnote">
              Выводы ограничены найденными источниками. Проверяйте технические детали по оригиналу.
            </p>
          </section>
          <SourceCards
            sources={sources?.sources ?? []}
            active={activeEvidence}
            evidence={evidence}
            loading={evidenceLoading}
            onEvidence={(_, id) => {
              if (sources) void citation(sources, id);
            }}
            onExplain={(source) => {
              if (sources) explain(source, sources);
            }}
          />
        </div>
      </main>
    </div>
  );
}
