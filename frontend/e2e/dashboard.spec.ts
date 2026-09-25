import { expect, test } from '@playwright/test';
import { mockCommon } from './helpers/mockApi';

test('dashboard exposes WordPress link on card and details', async ({ page }) => {
  await mockCommon(page);
  await page.route('**/jobs**', route => route.fulfill({ json: new URL(route.request().url()).searchParams.get('status_group') === 'active'
    ? { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 }
    : { items: [{ id: 'job-output', pipeline_id: 'p', pipeline_name: 'Publisher', status: 'success', progress: 100, current_step: 'Completed', logs: [], start_time: new Date().toISOString(), workflow_type: 'wp_publish', outputs: { wp_url: 'https://wp.test/post' }, capabilities: { can_cancel: false, can_rerun: false, can_open_draft: true, can_copy_link: true } }], total: 1, page: 1, page_size: 10, total_pages: 1 } }));
  await page.route('**/pipelines', route => route.fulfill({ json: [] }));
  await page.goto('/#/dashboard');
  await expect(page.getByTitle('Copy WordPress link')).toBeVisible();
  await page.getByRole('heading', { name: 'Publisher' }).click();
  await expect(page.getByText('WordPress output')).toBeVisible();
  await expect(page.getByTitle('Copy WordPress link')).toHaveCount(2);
});

test('dashboard paginates recent activity and requests the selected page', async ({ page }) => {
  await mockCommon(page);
  await page.route('**/jobs**', route => {
    const params = new URL(route.request().url()).searchParams;
    const requestedPage = params.get('page') || '1';
    if (params.get('status_group') === 'active') return route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 9, total_pages: 0 } });
    const items = requestedPage === '2'
      ? [{ id: 'job-11', pipeline_id: 'p', pipeline_name: 'Activity 11', status: 'success', progress: 100, current_step: 'Completed', logs: [], start_time: new Date().toISOString(), workflow_type: 'rewrite', outputs: {}, capabilities: { can_cancel: false, can_rerun: false, can_open_draft: false, can_copy_link: false } }]
      : Array.from({ length: 9 }, (_, index) => ({ id: `job-${index + 1}`, pipeline_id: 'p', pipeline_name: `Activity ${index + 1}`, status: 'success', progress: 100, current_step: 'Completed', logs: [], start_time: new Date().toISOString(), workflow_type: 'rewrite', outputs: {}, capabilities: { can_cancel: false, can_rerun: false, can_open_draft: false, can_copy_link: false } }));
    return route.fulfill({ json: { items, total: 10, page: Number(requestedPage), page_size: 9, total_pages: 2 } });
  });
  await page.route('**/pipelines', route => route.fulfill({ json: [] }));
  await page.goto('/#/dashboard');
  await expect(page.getByText('Page 1 of 2')).toBeVisible();
  await page.getByRole('button', { name: 'Next' }).click();
  await expect(page.getByText('Page 2 of 2')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Activity 11' })).toBeVisible();
});
