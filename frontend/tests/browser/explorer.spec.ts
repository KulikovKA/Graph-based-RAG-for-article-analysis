import { expect, test, type Page, type Route } from '@playwright/test';

const USER = '00000000-0000-4000-8000-000000000001';
const CONVERSATION = '00000000-0000-4000-8000-000000000002';
const RUN = '00000000-0000-4000-8000-000000000003';
const MESSAGE = '00000000-0000-4000-8000-000000000004';
const DOCUMENT = '00000000-0000-4000-8000-000000000005';
const REVISION = '00000000-0000-4000-8000-000000000006';
const EVIDENCE = '00000000-0000-4000-8000-000000000007';
const CHUNK = '00000000-0000-4000-8000-000000000008';
const node = {
  id: 'node-a',
  type: 'Technology',
  label: 'Охлаждение',
  evidence_ids: [EVIDENCE],
  document_id: DOCUMENT,
  revision_id: REVISION,
};
const neighbor = { id: 'node-b', type: 'Technology', label: 'Термодатчик', evidence_ids: [] };
const source = {
  document_id: DOCUMENT,
  revision_id: REVISION,
  title: 'Публикация о батарее',
  kind: 'article',
  url: 'https://openalex.org/W1',
  evidence_ids: [EVIDENCE],
};
const quote = 'Точная цитата 🔬';
const evidence = {
  evidence_id: EVIDENCE,
  document_id: DOCUMENT,
  revision_id: REVISION,
  chunk_id: CHUNK,
  section: 'abstract',
  span_start: 3,
  span_end: 3 + Array.from(quote).length,
  quoted_span: quote,
  source_url: source.url,
};
const nodes = [node, neighbor];
const edges = [
  {
    id: 'f',
    source: 'node-a',
    target: 'node-b',
    type: 'DISCLOSES_FEATURE',
    kind: 'factual',
    evidence_ids: [EVIDENCE],
  },
  {
    id: 's',
    source: 'node-b',
    target: 'node-a',
    type: 'SIMILAR_TO',
    kind: 'semantic',
    evidence_ids: [],
  },
];
const now = '2026-01-01T00:00:00Z';
const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
async function setup(page: Page) {
  const requests: URL[] = [],
    submitted: Record<string, unknown>[] = [];
  let error = 0;
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(),
      url = new URL(req.url()),
      path = url.pathname;
    requests.push(url);
    if (path.endsWith('/auth/session') || path.endsWith('/auth/login'))
      return json(route, { user_id: USER, csrf_token: 'csrf' });
    if (path.endsWith('/auth/logout')) return route.fulfill({ status: 204 });
    if (path === '/api/v1/conversations')
      return req.method() === 'POST'
        ? json(route, { id: CONVERSATION, title: 'Тест', created_at: now, updated_at: now }, 201)
        : json(route, { items: [], next_cursor: null });
    if (path.endsWith('/messages') && req.method() === 'POST') {
      submitted.push(req.postDataJSON());
      return json(
        route,
        {
          message_id: MESSAGE,
          run_id: RUN,
          status_url: `/api/v1/runs/${RUN}`,
          events_url: `/api/v1/runs/${RUN}/events`,
        },
        202,
      );
    }
    if (path === `/api/v1/runs/${RUN}`)
      return json(route, {
        id: RUN,
        status: 'completed',
        stage: 'completed',
        progress: {},
        idea_version_id: null,
        source_run_id: null,
        outcome: 'no_evidence',
        answer: null,
        public_analysis: null,
        answer_presentation: null,
        sources: [],
        coverage: { sources: [], channels: [], partial: false, historical: false },
        graph_url: null,
        created_at: now,
        completed_at: now,
        error_code: null,
      });
    if (path.startsWith('/api/v1/explorer/')) {
      if (error) return json(route, { error: { code: 'FAIL' } }, error);
      if (path.endsWith('/search')) {
        if (url.searchParams.get('q') === 'задержка')
          await new Promise((resolve) => setTimeout(resolve, 1000));
        const empty = !url.searchParams.get('q') || url.searchParams.get('q') === 'пусто';
        return json(route, {
          graph_version: 'v1',
          nodes: empty ? [] : [node],
          documents: empty ? [] : [source],
          next_cursor: null,
          truncated: false,
        });
      }
      if (path.endsWith('/neighbors')) {
        expect(
          edges.every(
            (edge) =>
              nodes.some((item) => item.id === edge.source) &&
              nodes.some((item) => item.id === edge.target),
          ),
        ).toBe(true);
        return json(route, {
          graph_version: 'v1',
          nodes,
          edges,
          next_cursor: null,
          truncated: false,
        });
      }
      if (path.endsWith('/paths')) return json(route, { graph_version: 'v1', nodes, edges: [edges[0]], next_cursor: null, truncated: false });
      if (path.includes('/nodes/'))
        return json(route, {
          graph_version: 'v1',
          node: path.endsWith('node-a') ? node : neighbor,
          context_ref: 'signed-secret-ref',
        });
      if (path.includes('/documents/'))
        return json(route, { graph_version: 'v1', source, nodes: [node] });
      if (path.includes('/evidence/')) {
        expect(Array.from(evidence.quoted_span).length).toBe(
          evidence.span_end - evidence.span_start,
        );
        return json(route, evidence);
      }
    }
    return json(route, { error: { code: 'NOT_FOUND' } }, 404);
  });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Какая у вас идея?' })).toBeVisible();
  return {
    requests,
    submitted,
    setError: (value: number) => {
      error = value;
    },
  };
}
async function switchMode(page: Page, mobile: boolean, name: string) {
  if (mobile) await page.getByRole('button', { name: 'Открыть диалоги' }).click();
  await page.getByRole('button', { name, exact: true }).click();
}

test('фильтр, путь, история и панели сохраняют версию и выбор', async ({ page }, info) => {
  const { requests } = await setup(page);
  await switchMode(page, info.project.name === 'mobile', 'Граф знаний');
  await page.getByLabel('Сущность или документ').fill('батарея');
  await page.getByRole('button', { name: 'Найти', exact: true }).click();
  await page.getByRole('button', { name: /Охлаждение Technology/ }).click();
  await page.getByRole('button', { name: 'Раскрыть соседей' }).click();
  await page.getByLabel('Тип связи').selectOption('DISCLOSES_FEATURE');
  await expect(page.getByText('Фактическая · DISCLOSES_FEATURE')).toBeVisible();
  await expect(page.getByText('Семантическая · SIMILAR_TO')).toHaveCount(0);
  await page.getByLabel('Путь к вершине').selectOption('node-b');
  await page.getByRole('button', { name: 'Найти путь' }).click();
  await expect.poll(() => requests.some((url) => url.pathname.endsWith('/paths'))).toBe(true);
  const path = requests.find((url) => url.pathname.endsWith('/paths'))!;
  expect(Object.fromEntries(path.searchParams)).toMatchObject({ source: 'node-a', target: 'node-b', max_hops: '3', edge_type: 'DISCLOSES_FEATURE', graph_version: 'v1' });
  await page.locator('.explorer-canvas').getByRole('button', { name: 'Термодатчик' }).click();
  await page.getByLabel('История выбора').getByRole('button', { name: 'Охлаждение' }).click();
  await expect(page.locator('.graph-details strong')).toHaveText('Охлаждение');
  await page.getByRole('button', { name: 'Развернуть граф' }).click();
  await expect(page.getByRole('button', { name: 'Вернуть панели' })).toBeVisible();
  await page.getByRole('button', { name: 'Вернуть панели' }).click();
  if (info.project.name === 'desktop') {
    await page.getByLabel('Ширина графа').fill('60');
    await page.getByLabel('Ширина списка диалогов').fill('280');
    await expect(page.getByRole('complementary', { name: 'Диалоги' })).toHaveCSS('width', '280px');
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('Explorer связывает документ, цитату, граф и подготовленный контекст', async ({
  page,
}, info) => {
  const { requests, submitted } = await setup(page),
    mobile = info.project.name === 'mobile';
  await page.getByLabel('Ваша идея или уточнение').fill('Тестовая идея');
  await switchMode(page, mobile, 'Граф знаний');
  await page.getByLabel('Сущность или документ').fill('батарея');
  await page.getByRole('button', { name: 'Найти', exact: true }).click();
  await page.getByRole('button', { name: /Публикация о батарее/ }).click();
  await expect(page.getByText(`Ревизия: ${REVISION}`)).toBeVisible();
  await page.getByRole('button', { name: 'Фрагмент 1' }).click();
  await expect(page.getByText(quote)).toBeVisible();
  await page.getByRole('button', { name: /Вершина: Охлаждение/ }).click();
  await expect(page.getByRole('button', { name: 'Раскрыть соседей' })).toBeVisible();
  await page.getByRole('button', { name: 'Раскрыть соседей' }).click();
  await expect(page.getByText('Фактическая · DISCLOSES_FEATURE')).toBeVisible();
  await expect(page.getByText('Семантическая · SIMILAR_TO')).toBeVisible();
  const canvas = page.locator('.explorer-canvas');
  const vertex = canvas.getByRole('button', { name: 'Охлаждение' });
  await vertex.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: 'Раскрыть соседей' })).toBeVisible();
  const transform = await canvas.locator(':scope > g').getAttribute('transform');
  await page.getByRole('button', { name: 'Увеличить граф' }).click();
  await expect(canvas.locator(':scope > g')).not.toHaveAttribute('transform', transform!);
  const zoomed = await canvas.locator(':scope > g').getAttribute('transform');
  const box = (await canvas.boundingBox())!;
  await page.mouse.move(box.x + 5, box.y + 5);
  await page.mouse.down();
  await page.mouse.move(box.x + 35, box.y + 25);
  await page.mouse.up();
  await expect(canvas.locator(':scope > g')).not.toHaveAttribute('transform', zoomed!);
  await page.getByRole('button', { name: 'Подготовить контекст' }).click();
  if (mobile) {
    await page.getByRole('button', { name: 'Документ и поиск' }).click();
    await page.getByRole('button', { name: 'Граф', exact: true }).click();
  }
  await expect(page.getByText('Контекст подготовлен для дальнейшего использования.')).toBeVisible();
  expect(
    requests.find((u) => u.pathname.includes('/documents/'))?.searchParams.get('revision_id'),
  ).toBe(REVISION);
  expect(
    requests
      .filter((u) => u.pathname.includes('/explorer/') && !u.pathname.endsWith('/search'))
      .every((u) => u.searchParams.get('graph_version') === 'v1'),
  ).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await switchMode(page, mobile, 'Ассистент');
  await expect(page.getByText(/Контекст «Охлаждение» подготовлен/)).toBeVisible();
  await expect(page.getByLabel('Ваша идея или уточнение')).toHaveValue('Тестовая идея');
  await page.getByRole('button', { name: 'Отправить запрос' }).click();
  await expect.poll(() => submitted.length).toBe(1);
  expect(submitted[0]).toEqual({
    content: 'Тестовая идея',
    expected_idea_version: 0,
    analyze: true,
  });
});

test('запоздалый ответ не переносится между областями', async ({ page }, info) => {
  const { requests } = await setup(page);
  const mobile = info.project.name === 'mobile';
  await page.getByLabel('Ваша идея или уточнение').fill('Тестовая идея');
  await page.getByRole('button', { name: 'Отправить запрос' }).click();
  await expect.poll(() => page.getByLabel('Ваша идея или уточнение').inputValue()).toBe('');
  await switchMode(page, mobile, 'Граф знаний');
  await page.getByLabel('Сущность или документ').fill('задержка');
  const started = page.waitForRequest(
    (req) => req.url().includes('/explorer/search') && req.url().includes('%D0'),
  );
  await page.getByRole('button', { name: 'Найти', exact: true }).click();
  await started;
  await page.getByLabel('Область').selectOption('run');
  await expect(page.getByText('Публикация о батарее')).toHaveCount(0);
  await page.waitForTimeout(1200);
  await expect(page.getByText('Публикация о батарее')).toHaveCount(0);
  await expect(page.getByText('Версия графа: v1')).toHaveCount(0);
  await page.getByLabel('Сущность или документ').fill('батарея');
  await page.getByRole('button', { name: 'Найти', exact: true }).click();
  await page.getByRole('button', { name: /Охлаждение Technology/ }).click();
  await expect(page.getByRole('button', { name: 'Раскрыть соседей' })).toBeVisible();
  const runSearch = requests.find(
    (u) => u.pathname.endsWith('/explorer/search') && u.searchParams.get('scope') === 'run',
  );
  expect(runSearch?.searchParams.get('run_id')).toBe(RUN);
  expect(runSearch?.searchParams.has('graph_version')).toBe(false);
  const runNode = requests.find(
    (u) => u.pathname.endsWith('/explorer/nodes/node-a') && u.searchParams.get('scope') === 'run',
  );
  expect(runNode?.searchParams.get('run_id')).toBe(RUN);
  expect(runNode?.searchParams.get('graph_version')).toBe('v1');
});

test('смена вершины и чата очищает подготовленный контекст', async ({ page }, info) => {
  await setup(page);
  const mobile = info.project.name === 'mobile';
  await page.getByLabel('Ваша идея или уточнение').fill('Тестовая идея');
  await page.getByRole('button', { name: 'Отправить запрос' }).click();
  await expect.poll(() => page.getByLabel('Ваша идея или уточнение').inputValue()).toBe('');
  await switchMode(page, mobile, 'Граф знаний');
  await page.getByLabel('Сущность или документ').fill('батарея');
  await page.getByRole('button', { name: 'Найти', exact: true }).click();
  await page.getByRole('button', { name: /Охлаждение Technology/ }).click();
  await page.getByRole('button', { name: 'Раскрыть соседей' }).click();
  await page.getByRole('button', { name: 'Подготовить контекст' }).click();
  await page.locator('.explorer-canvas').getByRole('button', { name: 'Термодатчик' }).click();
  await expect(page.getByText('Контекст подготовлен для дальнейшего использования.')).toHaveCount(
    0,
  );
  await switchMode(page, mobile, 'Ассистент');
  await expect(page.getByText(/Контекст «Охлаждение» подготовлен/)).toHaveCount(0);
  await switchMode(page, mobile, 'Граф знаний');
  await page.locator('.explorer-canvas').getByRole('button', { name: 'Охлаждение' }).click();
  await page.getByRole('button', { name: 'Подготовить контекст' }).click();
  if (mobile) await page.getByRole('button', { name: 'Открыть диалоги' }).click();
  await page.getByRole('button', { name: 'Новый диалог' }).click();
  await expect(page.getByText(/Контекст «Охлаждение» подготовлен/)).toHaveCount(0);
  await switchMode(page, mobile, 'Граф знаний');
  await expect(page.getByText('Контекст подготовлен для дальнейшего использования.')).toHaveCount(
    0,
  );
});

test('пустой поиск и ошибки оставляют доступный путь продолжения', async ({ page }, info) => {
  const fixture = await setup(page),
    mobile = info.project.name === 'mobile';
  await switchMode(page, mobile, 'Граф знаний');
  await page.getByLabel('Сущность или документ').fill('пусто');
  await page.getByRole('button', { name: 'Найти', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Ничего не найдено');
  for (const [code, text] of [
    [404, 'Объект недоступен'],
    [503, 'Граф временно недоступен'],
    [409, 'Версия графа устарела'],
  ] as const) {
    fixture.setError(code);
    await page.getByRole('button', { name: 'Найти', exact: true }).click();
    await expect(page.getByRole('status')).toContainText(text);
  }
  fixture.setError(0);
  await page.getByLabel('Сущность или документ').fill('батарея');
  await page.getByRole('button', { name: 'Найти', exact: true }).click();
  await expect(page.getByRole('button', { name: /Публикация о батарее/ })).toBeVisible();
  if (mobile) await page.getByRole('button', { name: 'Открыть диалоги' }).click();
  await page.getByRole('button', { name: 'Выйти', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Войти в пространство' })).toBeVisible();
  await expect(page.getByText('Публикация о батарее')).toHaveCount(0);
});

test('конфликт версии сбрасывает контекст, истечение сессии очищает граф', async ({
  page,
}, info) => {
  const fixture = await setup(page),
    mobile = info.project.name === 'mobile';
  await switchMode(page, mobile, 'Граф знаний');
  await page.getByLabel('Сущность или документ').fill('батарея');
  await page.getByRole('button', { name: 'Найти', exact: true }).click();
  await page.getByRole('button', { name: /Охлаждение Technology/ }).click();
  await page.getByRole('button', { name: 'Подготовить контекст' }).click();
  fixture.setError(409);
  await page.getByRole('button', { name: 'Раскрыть соседей' }).click();
  await expect(page.getByRole('status')).toContainText('Версия графа устарела');
  await switchMode(page, mobile, 'Ассистент');
  await expect(page.getByText(/Контекст «Охлаждение» подготовлен/)).toHaveCount(0);
  await switchMode(page, mobile, 'Граф знаний');
  fixture.setError(401);
  if (mobile) await page.getByRole('button', { name: 'Документ и поиск' }).click();
  await page.getByRole('button', { name: 'Найти', exact: true }).click();
  await expect(
    page.getByText('Сессия завершилась. Войдите снова, чтобы продолжить.'),
  ).toBeVisible();
  await expect(page.getByText('Охлаждение')).toHaveCount(0);
});
