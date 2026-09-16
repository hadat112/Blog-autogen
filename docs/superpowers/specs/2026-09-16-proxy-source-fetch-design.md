# Proxy Source Fetch Design

## Goal

Allow users to configure one shared HTTP/HTTPS proxy and selectively enable it for individual V1/V2 rewrite runs from the Dashboard. The proxy is intended to reach source article URLs affected by Cloudflare or network restrictions.

## Scope

- Add an optional `proxy_url` to the existing application Settings.
- Add a Dashboard switch with `use_proxy`, defaulting to off and persisted in browser local storage.
- Apply the proxy only to source article fetching.
- Keep AI, WordPress, Facebook, Telegram, and other outbound requests on the normal network path.
- Preserve backward compatibility: requests without `use_proxy` behave exactly as before.

## Backend design

`AppSettings` and the Settings API will expose `proxy_url`, nullable/empty when not configured. The existing settings persistence mechanism remains the source of truth.

Rewrite run payloads will accept `use_proxy: boolean = false`. The value will be passed through the unified article workflow service to the source gateway/importer. The source HTTP request will construct a requests-compatible proxy mapping only when both `use_proxy` is true and a configured proxy URL exists.

Proxy URLs must use `http://` or `https://` and may include authentication and a port. Credentials must never be written to job logs, error messages, or persisted job payloads. A malformed proxy URL is rejected during Settings save. A connection failure is reported as a source-fetch job error; there is no automatic fallback to the direct network path.

## Frontend design

Settings will add a `Proxy Settings` area with one proxy URL input and a Save action. The Dashboard Run workflow card will show a compact `Proxy OFF/ON` switch alongside the existing rewrite controls. The switch is shared by V1 and V2 because source ingestion is common.

The switch state is stored under a dedicated local-storage key and defaults to false. If enabled without a saved proxy URL, starting a job is blocked with a clear configuration message. The run request includes `use_proxy` for both V1 and V2.

## Data flow

```text
Settings UI -> PUT /settings -> persisted proxy_url
Dashboard switch -> POST /article-workflows/run { use_proxy }
                         |
                         v
              ArticleWorkflowService
                         |
                         v
             WordPressSourceGateway
                         |
                         v
              source fetch with proxy
```

## Compatibility and validation

- Existing Settings files without `proxy_url` load as empty.
- Existing run clients without `use_proxy` remain direct-fetch runs.
- Existing jobs are not modified.
- Proxy credentials are treated as secrets and excluded from logs.
- The change must not alter the AI or publishing clients.

## Verification

- Verify Settings round-trip with an empty and a valid proxy URL.
- Verify V1/V2 payloads preserve `use_proxy`.
- Verify source fetch receives proxies only when enabled.
- Verify AI and WordPress clients receive no proxy configuration.
- Verify the Dashboard switch persists across reloads and blocks runs when no proxy is configured.
