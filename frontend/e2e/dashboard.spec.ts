import { expect, test } from '@playwright/test';
import { mockCommon } from './helpers/mockApi';

test('dashboard exposes WordPress link on card and details', async ({ page }) => {
  await mockCommon(page);
  await page.route('**/jobs', route => route.fulfill({ json: [{ id: 'job-output', pipeline_id: 'p', pipeline_name: 'Publisher', status: 'success', progress: 100, current_step: 'Completed', logs: [], start_time: new Date().toISOString(), workflow_type: 'wp_publish', outputs: { wp_url: 'https://wp.test/post' }, capabilities: { can_cancel: false, can_rerun: false, can_open_draft: true, can_copy_link: true } }] }));
  await page.route('**/pipelines', route => route.fulfill({ json: [] }));
  await page.goto('/#/dashboard');
  await expect(page.getByTitle('Copy WordPress link')).toBeVisible();
  await page.getByRole('heading', { name: 'Publisher' }).click();
  await expect(page.getByText('WordPress output')).toBeVisible();
  await expect(page.getByTitle('Copy WordPress link')).toHaveCount(2);
});
