import { expect, test, type Page, type Route } from '@playwright/test';

const now = '2026-01-01T00:00:00Z';
const chat = 'chat-a', other = 'chat-b', run = 'run-a', second = 'run-b', submittedRun = 'run-submitted';
const json = (route: Route, value: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(value) });

async function setup(page: Page) {
  let fail = false;
  const grants: Record<string, boolean> = { [run]: false, [second]: false };
  const mutations: { method: string; body: unknown; csrf: string | undefined }[] = [];
  let release: (() => void) | undefined;
  let delay = false;
  let delaySubmitted = false;
  let releaseSubmitted: (() => void) | undefined;
  const consentRequests: string[] = [];
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname;
    if (path.endsWith('/auth/session')) return json(route, { user_id: 'alice', csrf_token: 'csrf' });
    if (path.endsWith('/auth/logout')) return route.fulfill({ status: 204 });
    if (path === '/api/v1/conversations') return json(route, { items: [chat, other].map((id) => ({ id, title: id, created_at: now, updated_at: now })), next_cursor: null });
    if (path.endsWith('/messages')) {
      if (req.method() === 'POST') return json(route, { message_id: 'message-submitted', run_id: submittedRun }, 202);
      return json(route, { items: [], next_cursor: null });
    }
    if (path === `/api/v1/conversations/${chat}` || path === `/api/v1/conversations/${other}`) return json(route, { id: path.split('/').pop(), title: path.split('/').pop(), idea: null, last_runs: [path.endsWith(chat) ? run : second], created_at: now, updated_at: now });
    if (path.endsWith('/external-consent')) {
      const id = path.split('/')[4];
      consentRequests.push(id);
      if (req.method() === 'GET' && delay && id === run) { delay = false; await new Promise<void>((resolve) => { release = resolve; }); }
      if (req.method() !== 'GET') {
        mutations.push({ method: req.method(), body: req.postData() ? req.postDataJSON() : null, csrf: req.headers()['x-csrf-token'] });
        if (fail) return json(route, { error: { code: 'INVALID_CSRF' } }, 403);
        grants[id] = req.method() === 'POST';
        if (req.method() === 'DELETE') return route.fulfill({ status: 204 });
      }
      return json(route, { notice_version: 'groq_context_v1', granted: grants[id] });
    }
    if (path === `/api/v1/runs/${submittedRun}` && delaySubmitted) {
      await new Promise<void>((resolve) => { releaseSubmitted = resolve; });
    }
    if (path.startsWith('/api/v1/runs/')) return json(route, { id: path.split('/')[4], status: 'completed', stage: 'completed', progress: {}, idea_version_id: null, source_run_id: null, outcome: 'no_evidence', answer: null, public_analysis: null, answer_presentation: null, sources: [], graph_url: null, coverage: { sources: [], channels: [], partial: false, historical: true }, created_at: now, completed_at: now, error_code: null });
    return json(route, { error: { code: 'NOT_FOUND' } }, 404);
  });
  await page.goto('/');
  return { mutations, consentRequests, fail: (v: boolean) => { fail = v; }, delay: () => { delay = true; }, release: () => release?.(), delaySubmitted: () => { delaySubmitted = true; }, releaseSubmitted: () => releaseSubmitted?.() };
}
async function open(page: Page, name: string, mobile: boolean) {
  if (mobile) await page.getByRole('button', { name: 'Открыть диалоги' }).click();
  await page.getByRole('navigation').getByRole('button', { name }).click();
}

test('согласие, отзыв и отказ CSRF', async ({ page }, info) => {
  const fixture = await setup(page);
  await open(page, chat, info.project.name === 'mobile');
  const panel = page.getByRole('region', { name: 'Согласие на внешнюю обработку' });
  await expect(panel).toContainText('Рабочая передача данных пока не включена');
  await expect(panel).toContainText('Разрешение не предоставлено');
  await panel.getByRole('button', { name: 'Разрешить внешнюю обработку' }).click();
  await expect(panel).toContainText('Разрешение сохранено');
  expect(fixture.mutations[0]).toEqual({ method: 'POST', body: { notice_version: 'groq_context_v1' }, csrf: 'csrf' });
  fixture.fail(true);
  await panel.getByRole('button', { name: 'Отозвать разрешение' }).click();
  await expect(panel.getByRole('alert')).toContainText('Обновите страницу');
  await expect(panel).toContainText('Состояние разрешения неизвестно');
  fixture.fail(false);
  await panel.getByRole('button', { name: 'Повторить проверку' }).click();
  await expect(panel).toContainText('Разрешение сохранено');
  await panel.getByRole('button', { name: 'Отозвать разрешение' }).click();
  await expect(panel).toContainText('Разрешение не предоставлено');
  expect(fixture.mutations.at(-1)).toEqual({ method: 'DELETE', body: null, csrf: 'csrf' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('поздний ответ запуска после отправки не изменяет другой чат', async ({ page }, info) => {
  const fixture = await setup(page);
  await open(page, chat, info.project.name === 'mobile');
  await expect(page.getByRole('region', { name: 'Согласие на внешнюю обработку' })).toContainText(run);
  fixture.delaySubmitted();
  const requested = page.waitForRequest((req) => req.url().endsWith(`/runs/${submittedRun}`));
  await page.getByLabel('Ваша идея или уточнение').fill('Синтетическая идея');
  await page.getByRole('button', { name: 'Отправить запрос' }).click();
  await requested;
  if (info.project.name === 'mobile') await page.getByRole('button', { name: 'Открыть диалоги' }).click();
  await page.getByRole('link', { name: 'Контекст Анализ публикаций' }).click();
  await open(page, other, info.project.name === 'mobile');
  const panel = page.getByRole('region', { name: 'Согласие на внешнюю обработку' });
  await expect(panel).toContainText(second);
  const response = page.waitForResponse((value) => value.url().endsWith(`/runs/${submittedRun}`));
  fixture.releaseSubmitted();
  await response;
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(panel).toContainText(second);
  await expect(page.getByText('Синтетическая идея', { exact: true })).toHaveCount(0);
  expect(fixture.consentRequests).not.toContain(submittedRun);
  await page.getByLabel('Ваша идея или уточнение').fill('Другой запрос');
  await expect(page.getByRole('button', { name: 'Отправить запрос' })).toBeEnabled();
});

test('поздний ответ другого чата не меняет выбранное исследование', async ({ page }, info) => {
  const fixture = await setup(page);
  fixture.delay();
  const first = page.waitForRequest((req) => req.url().endsWith(`/runs/${run}/external-consent`));
  await open(page, chat, info.project.name === 'mobile');
  await first;
  await open(page, other, info.project.name === 'mobile');
  const panel = page.getByRole('region', { name: 'Согласие на внешнюю обработку' });
  await expect(panel).toContainText('Разрешение не предоставлено');
  await panel.getByRole('button', { name: 'Разрешить внешнюю обработку' }).click();
  await expect(panel).toContainText('Разрешение сохранено');
  fixture.release();
  await expect(panel).toContainText('Разрешение сохранено');
});
