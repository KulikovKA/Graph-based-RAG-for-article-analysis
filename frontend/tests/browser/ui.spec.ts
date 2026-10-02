import { test, expect, type Page, type Route } from '@playwright/test';
import { createHash } from 'node:crypto';
import type { Claim, ConversationDetail, Message, Run, Source } from '../../src/api/types';

const ID = '00000000-0000-4000-8000-000000000001';
const EVIDENCE = '00000000-0000-4000-8000-000000000010';
const EVIDENCE2 = '00000000-0000-4000-8000-000000000011';
const NOW = '2026-10-02T10:00:00Z';
const TEXT =
  'В публикации описано управление охлаждением батареи.\nСовпадает использование датчика температуры; индивидуальные каналы требуют дополнительной проверки.';
const digest = (text: string) => createHash('sha256').update(text).digest('hex');
const sources: Source[] = [
  {
    document_id: 'paper',
    revision_id: 'revision-a',
    title: 'Thermal management of battery cells',
    kind: 'article',
    publication_date: '2024-01-01',
    url: 'https://openalex.org/W1',
    evidence_ids: [EVIDENCE],
  },
  {
    document_id: 'patent',
    revision_id: 'revision-b',
    title: 'Cooling channels for battery modules',
    kind: 'patent',
    publication_date: '2023-06-01',
    url: 'https://worldwide.espacenet.com/patent/search?q=pn%3DEP1',
    evidence_ids: [EVIDENCE2],
  },
];
const claim: Claim = {
  text: 'Охлаждение регулируется по показаниям датчика температуры.',
  evidence_ids: [EVIDENCE],
  quotes: [{ evidence_id: EVIDENCE, start: 0, end: 6, text: 'Цитата' }],
};
type Mode =
  | 'normal'
  | 'reconnect'
  | 'presentation'
  | 'no_evidence'
  | 'safe_fallback'
  | 'partial'
  | 'reset';

async function setup(page: Page, mode: Mode = 'normal') {
  let authenticated = false;
  const submitted: Record<string, unknown>[] = [];
  const cursors: string[] = [];
  const conversations: ConversationDetail[] = [];
  const messages: Message[] = [];
  const runs: Record<string, Run> = {};
  let connection = 0;
  let nextRun = 1;
  const makeRun = (id: string, historical = false): Run => ({
    id,
    status: 'pending',
    stage: 'accepted',
    progress: { schema_version: 1, attempt: 0, stage: 'accepted', phase: 'waiting', counts: {} },
    idea_version_id: null,
    source_run_id: historical ? ID : null,
    outcome: null,
    answer: null,
    public_analysis: null,
    answer_presentation: null,
    sources: [],
    graph_url: null,
    coverage: { sources: [], channels: [], partial: mode === 'partial', historical },
    created_at: NOW,
    completed_at: null,
    error_code: null,
  });
  function final(run: Run): Run {
    const empty = mode === 'no_evidence';
    const text = empty
      ? 'По найденным материалам подтверждений нет. Уточните технические признаки.'
      : TEXT;
    return {
      ...run,
      status: 'completed',
      stage: 'completed',
      idea_version_id: 'idea-1',
      outcome: empty ? 'no_evidence' : mode === 'safe_fallback' ? 'safe_fallback' : 'analysis',
      progress: {
        schema_version: 1,
        attempt: 1,
        stage: 'verification',
        phase: 'completed',
        stage_started_at: NOW,
        counts: { feature_count: 3, candidate_count: 12, selected_document_count: empty ? 0 : 2 },
      },
      answer: {
        schema_version: 1,
        summary: empty ? [] : [claim],
        matches: [],
        differences: [],
        limitations: [],
        followup_suggestions: [],
      },
      public_analysis: { schema_version: 1, items: empty ? [] : [claim], limitations: [] },
      answer_presentation: {
        schema_version: 1,
        renderer_version: 'test-v1',
        text,
        chunk_count: 2,
        presentation_id: digest('test-v1' + text),
        text_sha256: digest(text),
      },
      sources: empty ? [] : sources,
      graph_url: `/api/v1/runs/${run.id}/graph`,
      completed_at: NOW,
    };
  }
  const json = (route: Route, body: unknown, status = 200) =>
    route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
  const frame = (run: Run, seq: number, type: string, payload: Record<string, unknown>) =>
    `id: ${seq}\nevent: ${type}\ndata: ${JSON.stringify({ run_id: run.id, seq, at: NOW, payload: { schema_version: 1, ...payload } })}\n\n`;
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request(),
      path = new URL(request.url()).pathname;
    if (path.endsWith('/auth/session'))
      return json(
        route,
        authenticated
          ? { user_id: 'alice', csrf_token: 'csrf-test' }
          : { error: { code: 'UNAUTHENTICATED' } },
        authenticated ? 200 : 401,
      );
    if (path.endsWith('/auth/login')) {
      authenticated = true;
      return json(route, { user_id: 'alice', csrf_token: 'csrf-test' });
    }
    if (path.endsWith('/auth/logout')) {
      authenticated = false;
      return route.fulfill({ status: 204 });
    }
    if (path === '/api/v1/conversations') {
      if (request.method() === 'POST') {
        const body = request.postDataJSON();
        const conversation: ConversationDetail = {
          id: ID,
          title: body.title || 'Идея охлаждения',
          created_at: NOW,
          updated_at: NOW,
          idea: null,
          last_runs: [],
        };
        conversations.push(conversation);
        return json(route, conversation, 201);
      }
      return json(route, { items: conversations, next_cursor: null });
    }
    if (path === `/api/v1/conversations/${ID}`) return json(route, conversations[0]);
    if (path.endsWith('/messages')) {
      if (request.method() === 'POST') {
        const input = request.postDataJSON();
        submitted.push(input);
        expect(request.headers()['x-csrf-token']).toBe('csrf-test');
        expect(request.headers()['idempotency-key']).toBeTruthy();
        const id =
          nextRun === 1 ? ID : `00000000-0000-4000-8000-${String(nextRun).padStart(12, '0')}`;
        nextRun++;
        runs[id] = makeRun(id, Boolean(input.source_run_id));
        const message = {
          id: 'message-' + nextRun,
          content: input.content,
          role: 'user' as const,
          run_id: id,
          created_at: NOW,
        };
        messages.push(message);
        conversations[0].last_runs.unshift(id);
        return json(
          route,
          {
            message_id: message.id,
            run_id: id,
            status_url: `/api/v1/runs/${id}`,
            events_url: `/api/v1/runs/${id}/events`,
          },
          202,
        );
      }
      return json(route, { items: messages, next_cursor: null });
    }
    if (path.includes('/evidence/')) {
      const id = path.split('/').pop()!;
      return json(route, {
        evidence_id: id,
        document_id: id === EVIDENCE ? 'paper' : 'patent',
        revision_id: 'revision-a',
        chunk_id: 'chunk',
        section: 'abstract',
        span_start: 0,
        span_end: 20,
        quoted_span: 'Cooling uses temperature feedback. <img src=x onerror="alert(1)">',
        source_url: sources[0].url,
      });
    }
    const runId = path.split('/')[4],
      run = runs[runId];
    if (!run) return json(route, { error: { code: 'NOT_FOUND' } }, 404);
    if (path.endsWith('/graph/neighbors'))
      return json(route, {
        run_id: runId, graph_version: 'graph-v1',
        nodes: [
          { id: `technical:${runId}`, type: 'TechnicalFeature', label: 'Связанный технический признак', evidence_ids: [EVIDENCE] },
        ],
        edges: [
          { id: `discloses:${runId}`, source: 'document:paper', target: `technical:${runId}`, type: 'DISCLOSES_FEATURE', evidence_ids: [EVIDENCE] },
        ], next_cursor: null, truncated: false,
      });
    if (path.endsWith('/graph'))
      return json(route, {
        run_id: runId, graph_version: 'graph-v1',
        nodes: [
          { id: 'idea:version', type: 'Idea', label: 'Идея анализа', evidence_ids: [] },
          { id: 'feature:f1', type: 'IdeaFeature', label: 'Регулирование по температуре', feature_id: 'f1', evidence_ids: [] },
          { id: 'document:paper', type: 'ScientificWork', label: sources[0].title, document_id: 'paper', revision_id: 'revision-a', evidence_ids: [EVIDENCE] },
        ],
        edges: [
          { id: 'has:f1', source: 'idea:version', target: 'feature:f1', type: 'HAS_FEATURE', evidence_ids: [] },
          { id: 'matches:f1:paper', source: 'feature:f1', target: 'document:paper', type: 'MATCHES', evidence_ids: [EVIDENCE] },
        ], next_cursor: null, truncated: false,
      });
    if (path.endsWith('/cancel')) {
      runs[runId] = final(run);
      return json(route, { status: 'completed', cancel_requested: false });
    }
    if (path.endsWith('/events')) {
      connection++;
      cursors.push(request.headers()['last-event-id'] ?? '');
      const complete = final(run),
        presentation = complete.answer_presentation!;
      const progress = {
        schema_version: 1,
        attempt: 1,
        stage: 'analyzing',
        phase: 'started',
        stage_started_at: new Date().toISOString(),
        counts: { feature_count: 3, candidate_count: 12, selected_document_count: 2 },
      };
      const beginning = frame(run, 1, 'analyzing', { progress });
      if (mode === 'reconnect' && connection === 1) {
        runs[runId] = {
          ...run,
          status: 'running',
          stage: 'analyzing',
          progress: progress as Run['progress'],
        };
        return route.fulfill({ contentType: 'text/event-stream', body: beginning });
      }
      const mid = Math.floor(presentation.text.length / 2);
      let body =
        beginning +
        frame(run, 2, 'sources_ready', { sources: complete.sources, coverage: complete.coverage }) +
        frame(run, 3, 'verification', {
          phase: 'completed',
          scope: 'result',
          outcome: complete.outcome,
        }) +
        frame(run, 4, 'analysis_summary', { public_analysis: complete.public_analysis }) +
        frame(run, 5, 'answer_started', {
          presentation_id: presentation.presentation_id,
          renderer_version: presentation.renderer_version,
          text_sha256: presentation.text_sha256,
          chunk_count: 2,
        }) +
        frame(run, 6, 'answer_delta', {
          presentation_id: presentation.presentation_id,
          chunk_index: 0,
          text: presentation.text.slice(0, mid),
        });
      if (mode === 'presentation' && connection === 1) {
        // Проверенный committed ответ уже существует, доставлена только первая половина.
        runs[runId] = { ...run, status: 'running', stage: 'analyzing', sources: complete.sources };
        return route.fulfill({ contentType: 'text/event-stream', body });
      }
      if (mode === 'presentation' && connection > 1) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
      if (mode === 'reset')
        body = frame(run, 10, 'run_snapshot', { run: complete, high_water: 10, reset: true });
      else
        body +=
          frame(run, 7, 'answer_delta', {
            presentation_id: presentation.presentation_id,
            chunk_index: 1,
            text: presentation.text.slice(mid),
          }) + frame(run, 8, 'completed', { run: complete });
      runs[runId] = complete;
      conversations[0].idea = { id: 'idea-1', version_no: 1, normalized: {} };
      return route.fulfill({ contentType: 'text/event-stream', body });
    }
    return json(route, run);
  });
  return { submitted, cursors };
}

async function login(page: Page) {
  await page.goto('/');
  await page.getByLabel('Электронная почта').fill('alice@example.test');
  await page.getByLabel('Пароль', { exact: true }).fill('synthetic-password');
  await page.getByRole('button', { name: 'Войти в пространство' }).click();
  await expect(page.getByRole('heading', { name: 'Какая у вас идея?' })).toBeVisible();
}
async function send(page: Page, text = 'Система охлаждения батареи по температуре ячеек') {
  await page.getByLabel('Ваша идея или уточнение').fill(text);
  await page.getByRole('button', { name: 'Отправить запрос' }).click();
}

test('new request, citations, saved-source follow-up and responsive layout', async ({
  page,
}, info) => {
  const fixture = await setup(page);
  await login(page);
  await send(page);
  await expect(page.getByTestId('answer-text').first()).toHaveText(TEXT);
  await expect(page.getByText('Версия идеи 1')).toBeVisible();
  await page.getByRole('button', { name: 'Цитата 1 ↗' }).click();
  await expect(
    page.getByText('Cooling uses temperature feedback.', { exact: false }),
  ).toBeVisible();
  expect(await page.locator('.evidence-detail img').count()).toBe(0);
  await expect(page.getByRole('link', { name: 'Открыть источник ↗' }).first()).toHaveAttribute(
    'rel',
    'noopener noreferrer',
  );
  await page.screenshot({
    path: `../docs/validation/UI-001/${info.project.name}.png`,
    fullPage: true,
  });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.getByRole('button', { name: 'Объяснить этот источник' }).nth(1).click();
  await page.getByRole('button', { name: 'Отправить запрос' }).click();
  await expect(page.locator('.exchange')).toHaveCount(2);
  expect(fixture.submitted[1].source_run_id).toBe(ID);
  expect(fixture.submitted[1].expected_idea_version).toBe(1);
  await expect(page.getByText('По сохранённым источникам')).toBeVisible();
});

test('interactive graph expands, links citations and collapses on desktop and mobile', async ({ page }) => {
  await setup(page);
  await login(page);
  await send(page);
  await expect(page.getByRole('region', { name: 'Карта анализа' })).toBeVisible();
  await page.getByRole('button', { name: sources[0].title }).click();
  await page.getByRole('button', { name: 'Раскрыть один hop' }).click();
  const technicalNode = page.getByRole('button', { name: 'Связанный технический признак' });
  await expect(technicalNode).toBeVisible();
  await technicalNode.click();
  await expect(page.getByRole('button', { name: 'Открыть цитату 1' })).toBeVisible();
  await page.getByRole('button', { name: 'Открыть цитату 1' }).click();
  await expect(page.getByText('Cooling uses temperature feedback.', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Свернуть связи' }).click();
  await expect(technicalNode).toHaveCount(0);
});

test('reconnect resumes with cursor and does not duplicate answer', async ({ page }) => {
  const fixture = await setup(page, 'reconnect');
  await login(page);
  await send(page);
  await expect(page.getByText('Анализ продолжается', { exact: true })).toBeVisible();
  await expect(page.getByText('Восстанавливаем соединение…')).toBeVisible();
  await expect(page.getByTestId('answer-text')).toHaveText(TEXT);
  expect(fixture.cursors).toContain('1');
  await expect(page.getByTestId('answer-text')).toHaveCount(1);
});

test('cancel during presentation preserves completed answer and show-all works', async ({
  page,
}) => {
  await setup(page, 'presentation');
  await login(page);
  await send(page);
  await expect(page.getByText('Результат проверен — получаем ответ')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Показать целиком' })).toBeVisible();
  await page.getByRole('button', { name: 'Отменить анализ' }).click();
  await expect(page.getByTestId('answer-text')).toHaveText(TEXT);
  await expect(page.getByText('Ответ сохранён')).toBeVisible();
});

test('show-all and browser display milestones', async ({ page }) => {
  await setup(page, 'presentation');
  await login(page);
  await send(page);
  await expect(page.getByRole('button', { name: 'Показать целиком' })).toBeVisible();
  await expect(page.getByTestId('answer-text')).not.toHaveText('');
  await expect
    .poll(() =>
      page.evaluate(() => performance.getEntriesByType('mark').map((entry) => entry.name)),
    )
    .toContain(`analysis:${ID}:first_delta_display`);
  const marks = await page.evaluate(() =>
    performance.getEntriesByType('mark').map((entry) => entry.name),
  );
  expect(marks).toContain(`analysis:${ID}:first_progress_display`);
  expect(marks).toContain(`analysis:${ID}:first_summary_display`);
  await page.getByRole('button', { name: 'Показать целиком' }).click();
  await expect(page.getByRole('button', { name: 'Показать целиком' })).toHaveCount(0);
});

for (const mode of ['no_evidence', 'safe_fallback', 'partial', 'reset'] as const) {
  test(`${mode} result and reduced motion`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await setup(page, mode);
    await login(page);
    await send(page);
    await expect(page.getByTestId('answer-text')).toBeVisible();
    if (mode === 'no_evidence')
      await expect(page.getByText('Подтверждений не найдено.')).toBeVisible();
    if (mode === 'safe_fallback')
      await expect(page.getByText('Сокращённый ответ:', { exact: false })).toBeVisible();
    if (mode === 'partial')
      await expect(page.getByText('Неполное покрытие:', { exact: false })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Показать целиком' })).toHaveCount(0);
    await page.getByText('Ход анализа', { exact: false }).click();
    expect(await page.locator('body').innerText()).not.toContain('RAW_REASONING_SENTINEL');
  });
}

test('logout clears private conversation state', async ({ page }, info) => {
  await setup(page);
  await login(page);
  await send(page);
  await expect(page.getByText('Ответ сохранён')).toBeVisible();
  if (info.project.name === 'mobile')
    await page.getByRole('button', { name: 'Открыть диалоги' }).click();
  await page.getByRole('button', { name: 'Выйти', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Войти в пространство' })).toBeVisible();
  await expect(page.getByTestId('answer-text')).toHaveCount(0);
});
