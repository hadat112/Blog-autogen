import { expect, test } from '@playwright/test';
import { mockCommon } from './helpers/mockApi';

const failedJob = {
  id: 'manual-job', pipeline_id: 'pipeline-generate', pipeline_name: 'Generate pipeline',
  workflow_type: 'article_v1', input_text: null, input_type: 'prompt', status: 'failed',
  current_step: 'Failed', progress: 90, logs: [], outputs: {},
  start_time: '2026-11-09T08:00:00Z',
  capabilities: { can_rerun: true, can_cancel: false, can_open_draft: true, can_copy_link: false },
};

async function setup(page: import('@playwright/test').Page) {
  await mockCommon(page);
  await page.route('**/settings', route => route.fulfill({ json: { default_ai_enrichment: false } }));
  await page.route('**/jobs/manual-job', route => route.fulfill({ json: failedJob }));
}

async function openPipeline(page: import('@playwright/test').Page) {
  await page.goto('/#/wordpress-publisher');
  await page.getByRole('tab', { name: 'Pipeline workflow', exact: true }).click();
  await expect(page.getByLabel('Select Pipeline', { exact: true })).toHaveValue('pipeline-generate');
}

test('switching modes preserves both input forms without submitting', async ({ page }) => {
  await setup(page);
  await openPipeline(page);
  await page.getByLabel('Source title', { exact: true }).fill('Original title');
  await page.getByLabel('Source content', { exact: true }).fill('Paragraph one.\n\nParagraph two.');
  await page.getByRole('tab', { name: 'Direct publishing', exact: true }).click();
  await expect(page.getByLabel('WordPress account')).toBeVisible();
  await page.getByRole('tab', { name: 'Pipeline workflow', exact: true }).click();
  await expect(page.getByLabel('Source title', { exact: true })).toHaveValue('Original title');
  await expect(page.getByLabel('Source content', { exact: true })).toHaveValue('Paragraph one.\n\nParagraph two.');
  await expect(page.getByRole('button', { name: /Proxy/ })).toHaveCount(0);
});

test('manual pipeline posts multipart and resumes the saved job without a URL', async ({ page }) => {
  await setup(page);
  let body = '';
  await page.route('**/article-workflows/run-text', async route => {
    expect(route.request().headers()['content-type']).toContain('multipart/form-data');
    body = route.request().postData() ?? '';
    await route.fulfill({ json: { job_id: 'manual-job', draft_id: 'draft-manual', status: 'queued' } });
  });
  let retried = false;
  await page.route('**/article-workflows/manual-job/retry', route => {
    retried = true;
    return route.fulfill({ json: { job_id: 'manual-job-2', draft_id: 'draft-manual', status: 'queued' } });
  });
  await page.route('**/jobs/manual-job-2', route => route.fulfill({ json: { ...failedJob, id: 'manual-job-2', status: 'success', progress: 100, outputs: { wp_url: 'https://wp.test/story' } } }));
  await openPipeline(page);
  await page.getByRole('button', { name: 'V2', exact: true }).click();
  await page.getByLabel('Source title', { exact: true }).fill('Original title');
  await page.getByLabel('Source content', { exact: true }).fill('Paragraph one.\n\nParagraph two.');
  await page.getByRole('button', { name: 'Run workflow', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeVisible();
  expect(body).toContain('name="mode"\r\n\r\nv2');
  expect(body).toContain('Original title');
  expect(body).toContain('Paragraph two.');
  expect(body).not.toContain('name="source_url"');
  await page.getByRole('button', { name: 'Resume', exact: true }).click();
  await expect(page.getByTitle('Open WordPress link')).toBeVisible();
  expect(retried).toBe(true);
  await page.reload();
  await page.getByRole('tab', { name: 'Pipeline workflow', exact: true }).click();
  await expect(page.getByTitle('Open WordPress link')).toBeVisible();
});

test('failed intake retains text and image controls remain exclusive', async ({ page }) => {
  await setup(page);
  await page.route('**/article-workflows/run-text', route => route.fulfill({ status: 400, json: { detail: 'Image rejected' } }));
  await openPipeline(page);
  await expect(page.getByRole('button', { name: 'Run workflow', exact: true })).toBeDisabled();
  await page.getByLabel('Source title', { exact: true }).fill('Original');
  await page.getByLabel('Source content', { exact: true }).fill('Content');
  const file = page.getByLabel('Source image upload');
  await page.getByLabel('Source image URL', { exact: true }).fill('https://images.test/a.jpg');
  await expect(file).toBeDisabled();
  await page.getByRole('button', { name: 'Remove source image', exact: true }).click();
  await file.setInputFiles({ name: 'a.jpg', mimeType: 'image/jpeg', buffer: Buffer.from([255, 216, 255, 1]) });
  await expect(page.getByLabel('Source image URL', { exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Remove source image', exact: true }).click();
  await page.getByRole('button', { name: 'Run workflow', exact: true }).click();
  await expect(page.getByText('Image rejected', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Source content', { exact: true })).toHaveValue('Content');
});

test('Dashboard resumes a manual article without requiring input URL', async ({ page }) => {
  await setup(page);
  await page.route('**/jobs?**', route => route.fulfill({ json: {
    items: route.request().url().includes('status_group=history') ? [failedJob] : [],
    total: 1, page: 1, page_size: 9, total_pages: 1,
  } }));
  let retried = false;
  await page.route('**/article-workflows/manual-job/retry', route => {
    retried = true;
    return route.fulfill({ json: { job_id: 'new-job', draft_id: 'draft', status: 'queued' } });
  });
  await page.goto('/#/');
  await page.getByRole('button', { name: 'Resume', exact: true }).click();
  await expect.poll(() => retried).toBe(true);
});

test('manual input fits mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await setup(page);
  await openPipeline(page);
  await expect(page.getByLabel('Source content', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: '/tmp/story-publisher-pipeline-mobile.png', fullPage: true });
});

test('image upload and pending request survive switching modes', async ({ page }) => {
  await setup(page);
  let submitted = 0;
  let release: () => void = () => {};
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/article-workflows/run-text', async route => {
    submitted += 1;
    const body = route.request().postDataBuffer()?.toString() ?? '';
    expect(body).toContain('filename="photo.jpg"');
    expect(body).not.toContain('name="image_url"');
    await pending;
    await route.fulfill({ json: { job_id: 'manual-job', draft_id: 'draft', status: 'queued' } });
  });
  await openPipeline(page);
  await page.getByLabel('Source title', { exact: true }).fill('Title');
  await page.getByLabel('Source content', { exact: true }).fill('Body');
  await page.getByLabel('Source image upload').setInputFiles({ name: 'photo.jpg', mimeType: 'image/jpeg', buffer: Buffer.from([255, 216, 255, 1]) });
  await page.getByRole('button', { name: 'Run workflow', exact: true }).click();
  await expect.poll(() => submitted).toBe(1);
  await page.getByRole('tab', { name: 'Direct publishing', exact: true }).click();
  await page.getByRole('tab', { name: 'Pipeline workflow', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Starting…', exact: true })).toBeDisabled();
  await expect(page.getByLabel('Source content', { exact: true })).toHaveValue('Body');
  release();
  await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeVisible();
  expect(submitted).toBe(1);
});

test('version preference is shared with Dashboard and missing pipelines disable run', async ({ page }) => {
  await setup(page);
  await openPipeline(page);
  await page.getByRole('button', { name: 'V2', exact: true }).click();
  await page.getByRole('link', { name: 'Dashboard', exact: true }).click();
  await expect(page.getByRole('button', { name: 'V2', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.route('**/pipelines?**', route => route.fulfill({ json: [] }));
  await page.goto('/#/wordpress-publisher');
  await page.reload();
  await page.getByRole('tab', { name: 'Pipeline workflow', exact: true }).click();
  await page.getByLabel('Source title', { exact: true }).fill('Title');
  await page.getByLabel('Source content', { exact: true }).fill('Body');
  await expect(page.getByRole('button', { name: 'Run workflow', exact: true })).toBeDisabled();
});
