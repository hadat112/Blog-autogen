import type { Page, Route } from '@playwright/test';

export const profile = (type: string) => ({ id: `profile-${type}`, name: `${type} profile`, type, language: type === 'wp_publish' ? '' : 'English', step_accounts: { ai: 'ai1', wp: 'wp1' }, settings: {}, wp_category_id: null, is_active: true, created_at: new Date().toISOString() });
export const draft = (kind: 'rewrite' | 'generated' | 'manual', state = 'ready_for_review') => ({ id: `draft-${kind}`, pipeline_id: `profile-${kind === 'generated' ? 'generate_story' : kind === 'manual' ? 'wp_publish' : 'rewrite'}`, kind, source_url: kind === 'rewrite' ? 'https://source.test/story' : null, language: kind === 'manual' ? null : 'English', title: 'A new story', content: 'Opening suspense\n\nThe rest of the story.', caption: kind === 'manual' ? null : 'Opening suspense', image_kind: null, image_source: null, content_format: 'plain', category_id: null, wp_status: 'draft', state, error: null, version: 1, wp_post_id: state === 'wordpress_created' ? '42' : null, wp_url: state === 'wordpress_created' ? 'https://wp.test/story' : null, created_at: new Date().toISOString(), updated_at: new Date().toISOString() });

export async function mockCommon(page: Page) {
  await page.route('**/*', async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (!url.pathname.startsWith('/accounts') && !url.pathname.startsWith('/languages') && !url.pathname.startsWith('/workflow-profiles') && !url.pathname.startsWith('/content-drafts') && !url.pathname.startsWith('/jobs') && !url.pathname.startsWith('/rewrite-jobs') && !url.pathname.startsWith('/generation-jobs') && !url.pathname.startsWith('/patterns') && !url.pathname.startsWith('/theme-rules') && !url.pathname.startsWith('/pattern-collection-sources')) return route.continue();
    const json = (body: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    if (url.pathname === '/accounts') return json([{ id: 'ai1', name: 'AI', type: 'ai', config: {} }, { id: 'wp1', name: 'WP', type: 'wp', config: {} }]);
    if (url.pathname === '/languages') return json([{ code: 'en', display_name: 'English', is_active: true, created_at: new Date().toISOString() }]);
    if (url.pathname === '/workflow-profiles') return json([profile(url.searchParams.get('type') || 'rewrite')]);
    if (url.pathname.endsWith('/wp-categories')) return json([{ id: 7, name: 'Drama', count: 2 }]);
    if (url.pathname === '/jobs/job1') return json({ id: 'job1', pipeline_id: 'profile', pipeline_name: 'Workflow', status: 'success', progress: 100, current_step: 'Completed', logs: [], start_time: new Date().toISOString(), workflow_type: 'rewrite', outputs: {}, capabilities: { can_cancel: false, can_rerun: false, can_open_draft: true, can_copy_link: false } });
    return json([]);
  });
}
