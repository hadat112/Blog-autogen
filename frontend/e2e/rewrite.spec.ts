import { expect, test } from '@playwright/test';
import { mockCommon } from './helpers/mockApi';

const pipeline = {
  id: 'pipeline-v2', name: 'Rewrite pipeline', type: 'rewrite', language: 'Italian',
  step_accounts: { ai: 'ai1', wp: 'wp1' }, settings: {}, is_active: true,
};

test('dashboard starts V2 rewrite from a saved pipeline', async ({ page }) => {
  await mockCommon(page);
  await page.route('**/pipelines*', route => route.fulfill({ json: [pipeline] }));
  await page.route('**/article-workflows/run', route => route.fulfill({ json: { job_id: 'job-v2', draft_id: 'draft-v2', status: 'queued' } }));
  await page.goto('/#/dashboard');
  await page.getByRole('button', { name: 'V2' }).click();
  await page.getByRole('combobox').first().selectOption('pipeline-v2');
  await page.getByPlaceholder('Paste an article URL (https://...)...').fill('https://source.test/story?fbclid=tracking');
  const request = page.waitForRequest(request => request.url().includes('/article-workflows/run'));
  await page.getByRole('button', { name: 'Run' }).click();
  expect((await request).postDataJSON()).toMatchObject({ pipeline_id: 'pipeline-v2', source_url: 'https://source.test/story', mode: 'v2' });
});

test('legacy rewrite route redirects to the unified dashboard', async ({ page }) => {
  await mockCommon(page);
  await page.goto('/#/rewrite');
  await expect(page).toHaveURL(/#\/dashboard$/);
  await expect(page.getByText('Run workflow')).toBeVisible();
});
