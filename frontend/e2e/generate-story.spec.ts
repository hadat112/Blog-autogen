import { expect, test } from '@playwright/test';
import { draft, mockCommon } from './helpers/mockApi';

test('generate story has no manual theme input and opens review output', async ({ page }) => {
  await mockCommon(page);
  await page.route('**/generation-jobs', route => route.fulfill({ json: { job_id: 'job1', draft_id: 'draft-generated', status: 'queued' } }));
  await page.route('**/content-drafts/draft-generated', route => route.fulfill({ json: { ...draft('generated'), caption: 'Independent social caption' } }));
  await page.goto('/#/generate-story');
  await expect(page.getByLabel(/theme/i)).toHaveCount(0);
  await page.getByLabel('Pipeline').selectOption('pipeline-generate');
  await page.getByRole('button', { name: 'Generate new story' }).click();
  await expect(page.getByLabel('Title')).toHaveValue('A new story');
  await expect(page.getByLabel('Caption')).toHaveValue('Independent social caption');
  await expect(page.getByText('Caption differs from story opening')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create WP draft' })).toBeEnabled();
});

test('generate story can be cancelled from its progress panel', async ({ page }) => {
  await mockCommon(page);
  let status = 'running';
  await page.route('**/generation-jobs', route => route.fulfill({ json: { job_id: 'cancel-generation', draft_id: 'draft-generated', status: 'queued' } }));
  await page.route('**/jobs/cancel-generation', route => route.fulfill({
    json: {
      id: 'cancel-generation', pipeline_id: 'profile-generate_story', status, progress: 20,
      current_step: status === 'cancelled' ? 'Cancelled' : 'Choose story patterns',
      logs: [], start_time: new Date().toISOString(), workflow_type: 'generate_story', outputs: {},
      capabilities: { can_cancel: status === 'running', can_rerun: false, can_open_draft: true, can_copy_link: false },
    },
  }));
  await page.route('**/jobs/cancel-generation/cancel', route => { status = 'cancelled'; return route.fulfill({ json: { status } }); });
  await page.route('**/content-drafts/draft-generated', route => route.fulfill({ json: { ...draft('generated'), state: status === 'cancelled' ? 'generation_failed' : 'generating', error: status === 'cancelled' ? 'Generation was cancelled' : null } }));
  await page.goto('/#/generate-story');
  await page.getByLabel('Pipeline').selectOption('pipeline-generate');
  await page.getByRole('button', { name: 'Generate new story' }).click();
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByText('Generation cancelled. The draft was preserved for recovery.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cancel' })).toHaveCount(0);
});
