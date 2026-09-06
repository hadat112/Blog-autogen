import { expect, test } from '@playwright/test';
import { mockCommon } from './helpers/mockApi';

for (const width of [375, 768, 1440]) {
  test(`workflow shell fits ${width}px without page overflow`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockCommon(page);
    await page.goto('/#/wordpress-publisher');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
}

test('theme toggle and keyboard focus remain available', async ({ page }) => {
  await mockCommon(page);
  await page.goto('/#/rewrite');
  await page.getByTitle('Toggle Theme').click();
  await expect(page.locator('html')).toHaveClass(/dark/);
  await page.keyboard.press('Tab');
  const focused = await page.evaluate(() => document.activeElement?.tagName);
  expect(focused).not.toBe('BODY');
});
