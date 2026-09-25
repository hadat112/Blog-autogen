import { expect, test } from '@playwright/test';
import { draft, mockCommon } from './helpers/mockApi';

test('manual publisher writes, previews, and only shows copy link on success', async ({ page }) => {
  await mockCommon(page);
  const local = draft('manual');
  await page.route('**/content-drafts', route => route.request().method() === 'POST' ? route.fulfill({ json: local }) : route.fulfill({ json: [] }));
  await page.route('**/content-drafts/draft-manual', route => route.fulfill({ json: { ...local, version: 2 } }));
  await page.route('**/content-drafts/draft-manual/publish', route => route.fulfill({ json: draft('manual', 'wordpress_created') }));
  await page.goto('/#/wordpress-publisher');
  await page.getByLabel('WordPress account').selectOption('wp1');
  await page.getByRole('button', { name: 'New post draft' }).click();
  await page.getByLabel('Title').fill('Manual title');
  await page.getByLabel('Content').fill('<script>alert(1)</script><p>Safe copy</p>');
  await page.getByLabel(/Featured image URL/).fill('https://images.test/story.jpg');
  await expect(page.locator('input[type="file"]')).toBeDisabled();
  await page.getByLabel(/Featured image URL/).fill('');
  await expect(page.locator('input[type="file"]')).toBeEnabled();
  await page.getByRole('tab', { name: 'HTML' }).click();
  await page.getByRole('tab', { name: 'Preview' }).click();
  await expect(page.getByText('Safe copy')).toBeVisible();
  await page.getByRole('button', { name: 'Create WP draft' }).click();
  await expect(page.getByRole('button', { name: 'Copy link' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Copy caption' })).toHaveCount(0);
});
