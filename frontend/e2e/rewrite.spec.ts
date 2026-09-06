import { expect, test } from '@playwright/test';
import { draft, mockCommon } from './helpers/mockApi';

test('rewrite reaches review and exposes both copy actions after WordPress success', async ({ page }) => {
  await mockCommon(page);
  await page.route('**/rewrite-jobs', route => route.fulfill({ json: { job_id: 'job1', draft_id: 'draft-rewrite', status: 'queued' } }));
  await page.route('**/content-drafts/draft-rewrite', route => route.fulfill({ json: draft('rewrite', 'wordpress_created') }));
  await page.goto('/#/rewrite');
  await page.getByLabel('WordPress source URL').fill('https://source.test/story');
  await page.getByRole('button', { name: 'Start rewrite' }).click();
  await expect(page.getByRole('button', { name: 'Copy link' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Copy caption' })).toBeVisible();
});
