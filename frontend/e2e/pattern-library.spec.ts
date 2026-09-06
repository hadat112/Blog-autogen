import { expect, test } from '@playwright/test';
import { mockCommon } from './helpers/mockApi';

test('pattern library renders metrics, filters, and management tabs', async ({ page }) => {
  await mockCommon(page);
  await page.route('**/patterns/summary', route => route.fulfill({ json: { total: 3, completed: 2, recoverable: 1, distinct_themes: 2 } }));
  await page.route(/\/patterns\?.*/, route => route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 20 } }));
  await page.route('**/theme-rules', route => route.fulfill({ json: [] }));
  await page.route('**/pattern-collection-sources', route => route.fulfill({ json: [] }));
  await page.goto('/#/pattern-library');
  await expect(page.getByText('3', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Filter by exact theme')).toBeVisible();
  await page.getByRole('tab', { name: 'Theme rules' }).click();
  await expect(page.getByLabel('Keywords, comma separated')).toBeVisible();
  await page.getByRole('tab', { name: 'Collection sources' }).click();
  await expect(page.getByText('No eligible crawl or rewrite profiles.')).toBeVisible();
});
