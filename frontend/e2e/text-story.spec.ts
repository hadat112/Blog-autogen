import { expect, test } from '@playwright/test';
import { mockCommon } from './helpers/mockApi';

const now = new Date().toISOString();
const baseDraft = { id: 'story-1', pipeline_id: 'pipe', kind: 'text_story', language: 'Italian', title: 'The Door',
  content: '', caption: null, image_kind: null, image_source: null, content_format: 'plain', category_id: null,
  wp_status: 'draft', state: 'generating', error: null, version: 1, created_at: now, updated_at: now };
const artifacts = { source_text: 'A long source story.', rewrite_text: 'The door opened.', continuation_text: '',
  image_prompt: 'A woman beside a wooden door', prompt_version: 'text-story-v1',
  stage_status: { rewrite: 'completed', title: 'completed', image_prompt: 'completed', enhance: 'pending' } };

async function setup(page: import('@playwright/test').Page, state = 'generating') {
  await mockCommon(page);
  await page.route('**/pipelines*', route => route.fulfill({ json: [{ id: 'pipe', name: 'Story pipeline', type: 'rewrite', language: 'Italian', step_accounts: { ai: 'ai', wp: 'wp' }, settings: {}, is_active: true }] }));
  await page.route('**/content-drafts?*', route => route.fulfill({ json: { items: [], total: 0 } }));
  await page.route('**/content-drafts/story-1', route => route.fulfill({ json: { ...baseDraft, state } }));
  await page.route('**/text-story-jobs/story-1/artifacts', route => route.fulfill({ json: artifacts }));
  await page.route('**/text-story-jobs', route => route.fulfill({ json: { job_id: 'job-story', draft_id: 'story-1', status: 'queued' } }));
  await page.route('**/jobs/job-story', route => route.fulfill({ json: { id: 'job-story', status: state === 'generation_failed' ? 'failed' : 'running', progress: 65, current_step: 'enhance', logs: [], outputs: {}, start_time: now } }));
}

test('shows saved rewrite and image prompt before full draft', async ({ page }) => {
  await setup(page);
  await page.goto('/#/text-story');
  await page.getByLabel('Pipeline').selectOption('pipe');
  await page.getByLabel('Source story').fill('A long source story.');
  await page.getByRole('button', { name: 'Create story' }).click();
  await expect(page.getByRole('heading', { name: 'Short rewrite' })).toBeVisible();
  await expect(page.getByText('The door opened.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Image prompt' })).toBeVisible();
  await expect(page.getByText('Review & publish')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create WP draft' })).toHaveCount(0);
});

test('failed continuation keeps artifacts and offers retry', async ({ page }) => {
  await setup(page, 'generation_failed');
  await page.goto('/#/text-story');
  await page.getByLabel('Pipeline').selectOption('pipe');
  await page.getByLabel('Source story').fill('A long source story.');
  await page.getByRole('button', { name: 'Create story' }).click();
  await expect(page.getByText('The door opened.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry failed stage' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create WP draft' })).toHaveCount(0);
});
