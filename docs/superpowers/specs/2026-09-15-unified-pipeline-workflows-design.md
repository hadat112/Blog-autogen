# Unified Pipeline Workflows Design

## Goal

Unify the workflow UX around saved pipelines instead of separately managed workflow profiles. The dashboard will expose V1 and V2 modes using the same pipeline selector and input form. Rewrite V2 will auto-publish after AI processing. Generate Story and WordPress Publisher will also consume pipeline IDs directly.

## Compatibility principle

Existing workflow profiles are already stored as rows in the `pipelines` table. They will not be deleted or renamed during migration. Existing jobs and drafts keep their current `pipeline_id` and `workflow_type`, so historical records remain readable.

The migration removes the profile abstraction from active API/UI code, not the underlying data.

## Unified UX

- Dashboard becomes the single run screen with V1 and V2 tabs.
- Both tabs select a saved pipeline and accept the same URL/prompt input.
- V1 uses the existing legacy pipeline runner.
- V2 uses the rewrite/AI runner and automatically publishes to WordPress.
- Rewrite no longer renders profile management, draft editing, or manual publish controls.
- Generate Story and WordPress Publisher use saved pipelines directly; WordPress Publisher only requires a configured WP account.

## Backend changes

- Extend the pipeline listing/lookup used by the unified UI to include active rows currently classified as workflow profiles.
- Add pipeline-ID based start inputs for rewrite and generation; retain old profile-ID request handling only during the migration boundary if needed by existing clients.
- Resolve AI/WP accounts and category settings from the selected pipeline's existing `step_accounts` and `settings`.
- Make WordPress publishing resolve any valid pipeline by `draft.pipeline_id`, rather than requiring a profile API type.
- Run V2 rewrite through the existing workflow job and draft system, then publish automatically with explicit internal confirmation. The job completes only after WordPress publication succeeds.
- Keep old job workflow type values and pipeline IDs unchanged.

## Data migration

No destructive database migration is required. Existing `Pipeline` rows with `rewrite`, `generate_story`, or `wp_publish` types remain valid selectable pipelines. Any future schema migration must preserve their IDs and account/settings JSON.

## API/UI cleanup

After all consumers are migrated, remove the `workflow-profiles` routes, profile service, profile manager component, profile client methods, and profile-specific tests. Keep content draft and job APIs because they remain necessary for history, status, and error recovery.

## Error handling

- Reject V2 runs when the selected pipeline has no valid AI or WP account.
- Reject WordPress Publisher runs when the selected pipeline has no valid WP account.
- Record rewrite failures as generation failures and publishing failures as publish failures, with the job remaining non-successful.
- Preserve ambiguous WordPress results as recoverable `publish_unknown` states.

## Testing

- Pipeline listing includes legacy and formerly profile-based rows.
- Old jobs/drafts with existing pipeline IDs remain readable.
- V1 starts through the legacy runner.
- V2 starts with a pipeline ID, rewrites, auto-publishes, and records the WordPress URL.
- Missing AI/WP accounts fail validation without creating a false success.
- Generate Story and WordPress Publisher start using pipeline IDs.
- Frontend tests cover the unified V1/V2 selector and absence of profile-management UI.
