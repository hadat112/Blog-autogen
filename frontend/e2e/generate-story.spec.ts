import { expect, test } from '@playwright/test';
import { draft, mockCommon } from './helpers/mockApi';

test('generate story has no manual theme input and opens review output', async ({ page }) => {
  await mockCommon(page);
  await page.route('**/generation-jobs', route => route.fulfill({ json: { job_id: 'job1', draft_id: 'draft-generated', status: 'queued' } }));
  await page.route('**/content-drafts/draft-generated', route => route.fulfill({ json: draft('generated') }));
  await page.goto('/#/generate-story');
  await expect(page.getByLabel(/theme/i)).toHaveCount(0);
  await page.getByRole('button', { name: 'Generate new story' }).click();
  await expect(page.getByLabel('Title')).toHaveValue('A new story');
  await expect(page.getByLabel('Caption')).toHaveValue('Opening suspense');
});
