import { test, expect } from '@playwright/test';

test('тестовый граф: раскрытие источника, цитата и сброс', async ({ page }) => {
  await page.goto('/graph-demo.html');
  const graph = page.getByRole('region', { name: 'Карта анализа' });
  await expect(graph.locator('.graph-node')).toHaveCount(8);
  await graph.getByRole('button', { name: 'Обратная связь', exact: true }).filter({ visible: true }).click();
  await page.getByRole('button', { name: 'Раскрыть один hop' }).click();
  await expect(graph.locator('.graph-node')).toHaveCount(10);
  await page.getByRole('button', { name: 'Открыть цитату 1', exact: true }).click();
  await expect(page.getByRole('complementary', { name: 'Тестовая цитата' })).toContainText('100 мс');
  await page.getByRole('button', { name: 'Свернуть связи', exact: true }).click();
  await expect(graph.locator('.graph-node')).toHaveCount(8);
  await page.getByRole('button', { name: 'Сбросить вид и связи' }).click();
  await expect(graph.locator('.graph-details')).toHaveCount(0);
});

test('тестовый граф: масштабирование и перемещение поля', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'На телефоне граф представлен списком узлов.');
  await page.goto('/graph-demo.html');
  const canvas = page.getByRole('img', { name: 'Интерактивный граф связей' });
  const transform = canvas.locator(':scope > g');
  await expect(transform).toHaveAttribute('transform', 'translate(0 0) scale(1)');
  await page.getByRole('button', { name: 'Увеличить', exact: true }).click();
  await expect(transform).toHaveAttribute('transform', /scale\(1\.15\)/);
  const before = await transform.getAttribute('transform');
  const box = (await canvas.boundingBox())!;
  await page.mouse.move(box.x + 20, box.y + 20);
  await page.mouse.down();
  await page.mouse.move(box.x + 100, box.y + 65, { steps: 5 });
  await page.mouse.up();
  await expect(transform).not.toHaveAttribute('transform', before!);
  await page.getByRole('button', { name: 'Сбросить вид и связи' }).click();
  await expect(transform).toHaveAttribute('transform', 'translate(0 0) scale(1)');
});
