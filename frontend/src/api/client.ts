import type {
  Accepted,
  Conversation,
  ConversationDetail,
  Evidence,
  Message,
  MessageInput,
  Page,
  Run,
  Session,
} from './types';

export class ApiError extends Error {
  status: number;
  code: string;
  retryAfter: number;
  constructor(status: number, code: string, retryAfter = 0) {
    super(code);
    this.status = status;
    this.code = code;
    this.retryAfter = retryAfter;
  }
}

let csrf = '';
export function setSession(session: Session | null) {
  csrf = session?.csrf_token ?? '';
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!path.startsWith('/api/v1/') || path.startsWith('//')) throw new Error('INVALID_API_PATH');
  const headers = new Headers(options.headers);
  if (options.body) headers.set('Content-Type', 'application/json');
  if (options.method && options.method !== 'GET') headers.set('X-CSRF-Token', csrf);
  const response = await fetch(path, {
    ...options,
    headers,
    credentials: 'same-origin',
    cache: 'no-store',
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new ApiError(
      response.status,
      body.error?.code ?? 'REQUEST_FAILED',
      Number(response.headers.get('Retry-After') ?? 0),
    );
    if (response.status === 401 && !path.endsWith('/auth/login'))
      window.dispatchEvent(new Event('session-expired'));
    throw error;
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const api = {
  session: () => request<Session>('/api/v1/auth/session'),
  login: (email: string, password: string) =>
    request<Session>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<void>('/api/v1/auth/logout', { method: 'POST' }),
  conversations: (cursor?: string) =>
    request<Page<Conversation>>(
      '/api/v1/conversations' + (cursor ? '?cursor=' + encodeURIComponent(cursor) : ''),
    ),
  create: (title?: string) =>
    request<Conversation>('/api/v1/conversations', {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),
  conversation: (id: string) =>
    request<ConversationDetail>(`/api/v1/conversations/${encodeURIComponent(id)}`),
  messages: (id: string, cursor?: string) =>
    request<Page<Message>>(
      `/api/v1/conversations/${encodeURIComponent(id)}/messages` +
        (cursor ? '?cursor=' + encodeURIComponent(cursor) : ''),
    ),
  send: (id: string, input: MessageInput, key: string) =>
    request<Accepted>(`/api/v1/conversations/${encodeURIComponent(id)}/messages`, {
      method: 'POST',
      headers: { 'Idempotency-Key': key },
      body: JSON.stringify(input),
    }),
  run: (id: string) => request<Run>(`/api/v1/runs/${encodeURIComponent(id)}`),
  cancel: (id: string) =>
    request<{ status: Run['status']; cancel_requested: boolean }>(
      `/api/v1/runs/${encodeURIComponent(id)}/cancel`,
      { method: 'POST' },
    ),
  evidence: (run: string, id: string) =>
    request<Evidence>(`/api/v1/runs/${encodeURIComponent(run)}/evidence/${encodeURIComponent(id)}`),
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429)
      return `Слишком много запросов. Повторите через ${error.retryAfter || 60} с.`;
    const messages: Record<string, string> = {
      INVALID_CREDENTIALS: 'Проверьте почту и пароль.',
      INVALID_CSRF: 'Обновите страницу и повторите действие.',
      INVALID_ORIGIN: 'Вход с этого адреса не разрешён. Обратитесь к оператору.',
      HTTPS_REQUIRED: 'Откройте приложение по HTTPS.',
      VERSION_CONFLICT: 'Идея обновилась. Версия синхронизирована — повторите отправку.',
      RUN_IN_PROGRESS: 'В этом диалоге уже идёт анализ. Дождитесь результата или отмените его.',
      SOURCE_RUN_NOT_COMPLETED: 'Сначала дождитесь результата выбранного анализа.',
      NOT_FOUND: 'Диалог или источник недоступен.',
      UNAUTHENTICATED: 'Сессия завершилась. Войдите снова.',
    };
    return messages[error.code] ?? 'Запрос не выполнен. Попробуйте ещё раз.';
  }
  return 'Нет соединения с сервером. Проверьте сеть и повторите действие.';
}

export function randomKey(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (x) => x.toString(16).padStart(2, '0')).join('');
}
