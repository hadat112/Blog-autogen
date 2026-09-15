# Dashboard Recent Activity Pagination Design

## Goal

Allow the dashboard to retain and browse an unbounded job history while showing 10 records per page. Workflow filtering must happen in the backend before pagination so each filtered page contains up to 10 matching records.

## Current behavior

- `GET /jobs` returns a limited list ordered by newest start time.
- The dashboard fetches that list without pagination or workflow parameters.
- Recent Activity applies a client-side `.slice(0, 10)` limit.
- Workflow filtering is performed in the browser, so older records can be hidden by the API limit and a filtered view may contain fewer than 10 records even when more matches exist.

## Proposed design

### API and service

Extend `GET /jobs` with:

- `page`: one-based page number, default `1`.
- `page_size`: default `10`; constrain it to a safe positive range.
- `workflow_type`: optional filter. Omit it or use `all` for every workflow.

Return a paginated envelope:

```json
{
  "items": [],
  "total": 42,
  "page": 1,
  "page_size": 10,
  "total_pages": 5
}
```

The service applies the workflow filter in SQL, counts matching jobs, orders by `start_time DESC` and `id DESC` for stable ordering, then applies offset/limit. Existing single-job behavior remains unchanged.

### Dashboard behavior

- Fetch jobs using the active page and workflow filter.
- Remove client-side workflow filtering and the Recent Activity `.slice(0, 10)` limit.
- Render the returned `items` as Active Tasks and Recent Activity.
- Keep the current page during polling and refetches.
- Reset to page 1 when the workflow filter changes.
- Show Previous/Next controls and the current range/total. Disable Previous on page 1 and Next on the last page.
- Preserve the existing empty state and job actions.

The server response is the source of truth for `total_pages`; the UI must not infer pagination from the current item count.

## Data flow

1. Dashboard state holds `page` and `workflowFilter`.
2. React Query uses both values in its query key.
3. The API receives `page`, `page_size=10`, and the workflow filter.
4. The backend filters and paginates the jobs table.
5. The dashboard renders the returned page and pagination metadata.

## Error handling and compatibility

- Invalid page values are rejected or normalized through FastAPI validation; the implementation will use validation that prevents non-positive values.
- A page beyond the last page returns an empty `items` list with accurate metadata; after a refresh, the UI may clamp the page if the total has decreased.
- Existing callers of `GET /jobs` should remain compatible through defaults, but the frontend will use the paginated envelope explicitly.
- Existing unsaved user changes in the worktree are out of scope and must not be modified.

## Testing

- Service/API tests verify total count, stable ordering, page boundaries, and workflow filtering before pagination.
- Frontend tests verify that the dashboard requests page/filter parameters, renders 10-record pages, changes pages, and resets to page 1 when the filter changes.
- Run the relevant Python API/service tests and frontend typecheck/test suite available in the repository.

## Scope exclusions

- No data migration is required because jobs are already stored in the database.
- No cursor pagination, page-size selector, deletion/retention policy, or historical export is included.
