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

test('rewrite can be cancelled from its progress panel', async ({ page }) => {
  await mockCommon(page);
  let status = 'running';
  await page.route('**/rewrite-jobs', route => route.fulfill({ json: { job_id: 'cancel-rewrite', draft_id: 'draft-rewrite', status: 'queued' } }));
  await page.route('**/jobs/cancel-rewrite', route => route.fulfill({
    json: {
      id: 'cancel-rewrite', pipeline_id: 'profile-rewrite', status, progress: 35,
      current_step: status === 'cancelled' ? 'Cancelled' : 'Rewrite chunk 1/3',
      logs: [], start_time: new Date().toISOString(), workflow_type: 'rewrite', outputs: {},
      capabilities: { can_cancel: status === 'running', can_rerun: false, can_open_draft: true, can_copy_link: false },
    },
  }));
  await page.route('**/jobs/cancel-rewrite/cancel', route => { status = 'cancelled'; return route.fulfill({ json: { status } }); });
  await page.route('**/content-drafts/draft-rewrite', route => route.fulfill({ json: { ...draft('rewrite'), state: status === 'cancelled' ? 'generation_failed' : 'generating', error: status === 'cancelled' ? 'Generation was cancelled' : null } }));
  await page.goto('/#/rewrite');
  await page.getByLabel('WordPress source URL').fill('https://source.test/story');
  await page.getByRole('button', { name: 'Start rewrite' }).click();
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByText('Rewrite cancelled. The draft was preserved for recovery.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cancel' })).toHaveCount(0);
});
