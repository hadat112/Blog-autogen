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

test('pattern retry defaults to an eligible AI source and shows retry errors', async ({ page }) => {
  await mockCommon(page);
  const article = { id: 'article-1', source_url: 'https://source.test/story', original_title: 'Story', theme_tags: ['family'], structure: null, word_count: 500, analysis_status: 'failed', analysis_error: 'Provider unavailable', processed_at: new Date().toISOString(), updated_at: new Date().toISOString() };
  await page.route('**/patterns/summary', route => route.fulfill({ json: { total: 1, completed: 0, recoverable: 1, distinct_themes: 1 } }));
  await page.route(/\/patterns\?.*/, route => route.fulfill({ json: { items: [article], total: 1, page: 1, page_size: 20 } }));
  await page.route('**/theme-rules', route => route.fulfill({ json: [] }));
  await page.route('**/pattern-collection-sources', route => route.fulfill({ json: [
    { pipeline_id: 'no-ai', name: 'Missing AI', type: 'crawl', collect_patterns: false, can_analyze: false },
    { pipeline_id: 'eligible', name: 'Ready source', type: 'rewrite', collect_patterns: true, can_analyze: true },
  ] }));
  await page.route('**/patterns/article-1/retry-analysis**', route => route.fulfill({ status: 400, json: { detail: 'Collection source has no valid AI account' } }));
  await page.goto('/#/pattern-library');
  await expect(page.getByLabel('AI profile for retry')).toHaveValue('eligible');
  await expect(page.locator('option[value="no-ai"]')).toHaveAttribute('disabled', '');
  await page.getByTitle('Retry analysis').click();
  await expect(page.getByRole('alert')).toContainText('Collection source has no valid AI account');
});
