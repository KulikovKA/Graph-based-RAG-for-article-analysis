import { expect, test, type Page, type Route } from '@playwright/test';

const chat = '00000000-0000-4000-8000-000000000001';
const run = '00000000-0000-4000-8000-000000000002';
const oldRun = '00000000-0000-4000-8000-000000000003';
const now = '2026-01-01T00:00:00Z';
const json = (route: Route, value: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(value) });

async function setup(page: Page) {
  let title: string | null = 'Первый чат', deleted = false, deny = false, denyExport = false, denyRun = false;
  const mutations: { method: string; body: unknown; csrf: string | undefined }[] = [];
  const cursors: (string | null)[] = [];
  const conversation = () => ({ id: chat, title, created_at: now, updated_at: now });
  const historyItem = (id: string) => ({ id, status: 'completed', outcome: 'no_evidence', created_at: now, completed_at: now, idea_version_id: 'idea-v1', index_generation_id: 'index-v1' });
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname;
    if (path.endsWith('/auth/session')) return json(route, { user_id: 'alice', csrf_token: 'csrf' });
    if (path === '/api/v1/conversations') return json(route, { items: deleted ? [] : [conversation()], next_cursor: null });
    if (path === `/api/v1/conversations/${chat}`) {
      if (req.method() === 'PATCH' || req.method() === 'DELETE') {
        mutations.push({ method: req.method(), body: req.postDataJSON(), csrf: req.headers()['x-csrf-token'] });
        if (deny) return json(route, { error: { code: 'INVALID_CSRF' } }, 403);
        if (req.method() === 'DELETE') { deleted = true; return route.fulfill({ status: 204 }); }
        title = req.postDataJSON().title; return json(route, conversation());
      }
      return json(route, { ...conversation(), idea: null, last_runs: [] });
    }
    if (path.endsWith('/messages')) return json(route, { items: [], next_cursor: null });
    if (path.endsWith('/runs')) {
      const cursor = url.searchParams.get('cursor'); cursors.push(cursor);
      return json(route, cursor ? { items: [historyItem(oldRun)], next_cursor: null } : { items: [historyItem(run)], next_cursor: 'next' });
    }
    if (path.endsWith('/export')) return denyExport ? json(route, { error: { code: 'RUN_NOT_COMPLETED' } }, 409) : route.fulfill({ status: 200, contentType: url.searchParams.get('format') === 'pdf' ? 'application/pdf' : 'text/html', headers: { 'Content-Disposition': 'attachment; filename="report.txt"' }, body: 'fixture' });
    if (path.endsWith('/external-consent')) return json(route, { notice_version: 'groq_context_v1', granted: false });
    if (path === `/api/v1/runs/${oldRun}` && denyRun) return json(route, { error: { code: 'NOT_FOUND' } }, 404);
    if (path.startsWith('/api/v1/runs/')) return json(route, {
      id: path.split('/')[4], status: 'completed', stage: 'completed', progress: {}, idea_version_id: null,
      source_run_id: null, outcome: 'no_evidence', answer: null, public_analysis: null, answer_presentation: null,
      sources: [], graph_url: null, coverage: { sources: [], channels: [], partial: false, historical: true },
      created_at: now, completed_at: now, error_code: null,
    });
    return json(route, { error: { code: 'NOT_FOUND' } }, 404);
  });
  await page.goto('/');
  return { mutations, cursors, setDeny: (value: boolean) => { deny = value; }, setDenyExport: (value: boolean) => { denyExport = value; }, setDenyRun: (value: boolean) => { denyRun = value; } };
}
async function openChat(page: Page, mobile: boolean) {
  if (mobile) await page.getByRole('button', { name: 'Открыть диалоги' }).click();
  await page.getByRole('button', { name: /Первый чат/ }).click();
}

test('переименование, история, экспорт и удаление используют контракт', async ({ page }, info) => {
  const fixture = await setup(page);
  await openChat(page, info.project.name === 'mobile');
  await page.getByRole('button', { name: 'Переименовать' }).click();
  await page.getByLabel('Название диалога').fill('Новое название');
  await page.getByRole('button', { name: 'Сохранить', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Новое название' })).toBeVisible();
  expect(fixture.mutations[0]).toEqual({ method: 'PATCH', body: { title: 'Новое название' }, csrf: 'csrf' });
  await page.getByRole('button', { name: 'Переименовать' }).click();
  await page.getByRole('button', { name: 'Сбросить название' }).click();
  expect(fixture.mutations[1].body).toEqual({ title: null });
  await page.getByRole('button', { name: 'История исследований' }).click();
  await expect(page.getByText(/Версия идеи: idea-v1 · Индекс: index-v1/)).toBeVisible();
  await page.getByRole('button', { name: 'Ещё исследования' }).click();
  expect(fixture.cursors).toEqual([null, 'next']);
  await page.locator('.history-item button').first().click();
  await expect(page.getByRole('region', { name: 'Согласие на внешнюю обработку' })).toContainText(run);
  await page.locator('.history-item button').nth(1).click();
  await expect(page.getByRole('region', { name: 'Согласие на внешнюю обработку' })).toContainText(oldRun);
  for (const format of ['HTML', 'PDF']) {
    const request = page.waitForRequest((req) => req.url().includes(`/export?format=${format.toLowerCase()}`));
    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: `Скачать ${format}` }).click();
    await request; await download;
  }
  page.once('dialog', (dialog) => void dialog.accept());
  await page.getByRole('button', { name: 'Удалить диалог' }).click();
  await expect(page.getByRole('heading', { name: 'Какая у вас идея?' })).toBeVisible();
  expect(fixture.mutations[2].method).toBe('DELETE');
  expect(fixture.mutations[2].csrf).toBe('csrf');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('отказ CSRF не меняет название и не удаляет диалог', async ({ page }, info) => {
  const fixture = await setup(page);
  await openChat(page, info.project.name === 'mobile');
  fixture.setDeny(true);
  await page.getByRole('button', { name: 'Переименовать' }).click();
  await page.getByLabel('Название диалога').fill('Новое название');
  await page.getByRole('button', { name: 'Сохранить', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Обновите страницу');
  await expect(page.getByRole('heading', { name: 'Первый чат' })).toBeVisible();
  page.once('dialog', (dialog) => void dialog.accept());
  await page.getByRole('button', { name: 'Удалить диалог' }).click();
  await expect(page.getByRole('alert')).toContainText('Обновите страницу');
  await expect(page.getByRole('heading', { name: 'Первый чат' })).toBeVisible();
});

test('ошибка экспорта отображается вместо скачивания', async ({ page }, info) => {
  const fixture = await setup(page);
  await openChat(page, info.project.name === 'mobile');
  await page.getByRole('button', { name: 'История исследований' }).click();
  await page.locator('.history-item button').first().click();
  fixture.setDenyExport(true);
  await page.getByRole('button', { name: 'Скачать PDF' }).click();
  await expect(page.getByRole('alert')).toContainText('Запрос не выполнен');
});

test('ошибка открытия истории не меняет выбранное согласие', async ({ page }, info) => {
  const fixture = await setup(page);
  await openChat(page, info.project.name === 'mobile');
  await page.getByRole('button', { name: 'История исследований' }).click();
  await page.getByRole('button', { name: 'Ещё исследования' }).click();
  await page.locator('.history-item button').first().click();
  const panel = page.getByRole('region', { name: 'Согласие на внешнюю обработку' });
  await expect(panel).toContainText(run);
  fixture.setDenyRun(true);
  await page.locator('.history-item button').nth(1).click();
  await expect(page.getByRole('region', { name: 'Управление диалогом' }).getByRole('alert')).toBeVisible();
  await expect(panel).toContainText(run);
});
