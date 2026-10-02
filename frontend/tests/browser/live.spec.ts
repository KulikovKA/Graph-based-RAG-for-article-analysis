import { test, expect } from '@playwright/test';

test('built UI through Caddy with real auth, API, PostgreSQL and synthetic worker', async ({
  page,
}, info) => {
  const url = process.env.UI_SMOKE_URL;
  test.skip(!url, 'UI_SMOKE_URL is not configured');
  await page.goto(url!);
  await page.getByLabel('Электронная почта').fill('ui-smoke@example.test');
  await page.getByLabel('Пароль', { exact: true }).fill('synthetic-smoke-password');
  await page.getByRole('button', { name: 'Войти в пространство' }).click();
  await expect(page.getByRole('heading', { name: 'Какая у вас идея?' })).toBeVisible();
  const title = `Синтетическая идея для проверки интерфейса ${info.project.name}`;
  await page.getByLabel('Ваша идея или уточнение').fill(title);
  await page.getByRole('button', { name: 'Отправить запрос' }).click();
  await expect(page.getByText('Ответ сохранён')).toHaveCount(1);
  await expect(page.getByText('Версия идеи 1')).toBeVisible();
  await page.getByLabel('Ваша идея или уточнение').fill('Уточнение технической идеи');
  await page.getByRole('button', { name: 'Отправить запрос' }).click();
  await expect(page.getByText('Ответ сохранён')).toHaveCount(2);
  await expect(page.getByText('Версия идеи 2')).toBeVisible();
  await page.reload();
  // Cookie session и durable история сохраняются после перезагрузки.
  if (page.viewportSize()!.width === 375)
    await page.getByRole('button', { name: 'Открыть диалоги' }).click();
  await page.getByRole('button', { name: new RegExp(title) }).click();
  await expect(page.getByText('Ответ сохранён')).toHaveCount(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});
