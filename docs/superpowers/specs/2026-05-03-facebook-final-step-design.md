# Facebook Publishing Integration at Final Pipeline Step

## 1. Objective
Add a dedicated Facebook Page publishing module to the existing story pipeline so that, after prior steps complete, the system posts **caption + image (if available)** to Facebook, then optionally comments the WordPress link on that Facebook post, and finally sends a Telegram status summary with per-step success/failure markers.

## 2. Scope
In scope:
- Add Facebook configuration fields to onboarding and config storage.
- Add a dedicated `FacebookPagePublisher` module (separate from orchestrator).
- Insert Facebook publishing before Telegram notification.
- Update Telegram notification format to show step-by-step status (`✅/❌/⚪`).
- Keep pipeline resilient: Facebook failures must not crash the whole run.

Out of scope:
- Scheduling posts.
- Multi-photo posts/albums.
- Publishing to Facebook Profile.
- Advanced retry queues.

## 3. Existing Flow (Current)
Current orchestrator flow in `core/orchestrator.py`:
1. AI text generation
2. AI image generation
3. WordPress publish
4. Google Sheets logging
5. Telegram notification

## 4. Target Flow (After Change)
New flow:
1. AI text generation
2. AI image generation
3. WordPress publish
4. Google Sheets logging
5. **Facebook publish (new)**
   - Prefer: photo + caption
   - Fallback: text post (caption only) if no usable image
   - Optional comment with `wp_url` only when `wp_url` exists
6. **Telegram notification (updated format)**
   - Summarize each step with status symbol and short error details

## 5. Design Details

### 5.1 Configuration & Onboarding
File: `core/config_manager.py`

Add config keys:
- `facebook_page_id`
- `facebook_page_access_token`
- `facebook_graph_version` (default `v23.0`)

Onboarding behavior:
- Prompt user for the three Facebook fields.
- Persist values into `config.yaml` via existing save flow.
- Validation style aligns with existing onboarding pattern:
  - Basic validation (non-empty, simple format checks).
  - Optional API check; on failure, allow user to retry/skip/cancel similar to current validator behavior.

### 5.2 New Publisher Module
New file: `publishers/facebook_page.py`

Class: `FacebookPagePublisher`

Constructor:
- Inputs: `page_id`, `access_token`, `graph_version='v23.0'`
- Build base API URL: `https://graph.facebook.com/{graph_version}`

Methods:
1. `publish_photo_caption(caption: str, image_url: str) -> str`
   - Endpoint: `POST /{page_id}/photos`
   - Payload includes:
     - `url` (remote image URL)
     - `caption`
     - `published=true`
     - `access_token`
   - Return created post id / media id suitable for follow-up comment target.

2. `publish_text(caption: str) -> str`
   - Endpoint: `POST /{page_id}/feed`
   - Payload:
     - `message=caption`
     - `access_token`
   - Used as fallback when image missing/fails.

3. `comment_on_post(post_id: str, message: str) -> str`
   - Endpoint: `POST /{post_id}/comments`
   - Payload:
     - `message`
     - `access_token`
   - Returns comment id.

Error behavior:
- Raise clear exceptions with HTTP status + response body snippets.
- No silent swallow inside publisher; orchestrator handles partial-failure behavior.

### 5.3 Orchestrator Integration
File: `core/orchestrator.py`

Initialization:
- Instantiate `FacebookPagePublisher` using config values.

Runtime state additions in `process_prompt`:
- Track step status fields, for example:
  - `ai_text_ok`, `ai_image_ok`, `wp_ok`, `sheets_ok`, `fb_post_ok`, `fb_comment_state`
  - error strings per failed step
- Maintain `fb_post_id` and optional `fb_comment_id`.

Step behavior:
- After Sheets step, run Facebook step.
- Facebook posting logic:
  - If image URL exists: try `publish_photo_caption(caption, image_url)`.
  - If image URL missing or photo publish fails: fallback `publish_text(caption)`.
- Comment logic:
  - If `wp_url` exists and a Facebook post was created, call `comment_on_post(post_id, wp_url)`.
  - If `wp_url` missing: mark comment state as skipped (`⚪`).

Failure policy:
- Facebook post/comment failure should set partial status but continue to Telegram.
- Preserve existing overall behavior of not crashing entire batch item unless critical earlier failure occurs.

### 5.4 Telegram Format Update
File: `core/orchestrator.py` (existing Telegram message block)

New Telegram message layout:
- Header with title.
- Step checklist lines:
  - `✅ AI text` or `❌ AI text: <reason>`
  - `✅ AI image` or `❌ AI image: <reason>`
  - `✅ WordPress` or `❌ WordPress: <reason>`
  - `✅ Google Sheets` or `❌ Google Sheets: <reason>`
  - `✅ Facebook post` or `❌ Facebook post: <reason>`
  - `✅ FB comment wp_url` / `❌ FB comment: <reason>` / `⚪ FB comment skipped (no wp_url)`
- Footer with key links/ids when available:
  - WP URL
  - Facebook Post ID

Formatting uses existing HTML-safe style compatible with `send_telegram_msg` usage.

### 5.5 Config File Implications
File: `config.yaml` (runtime generated)

Expected new entries in user config after onboarding:
- `facebook_page_id: ...`
- `facebook_page_access_token: ...`
- `facebook_graph_version: v23.0`

No breaking changes for existing keys.

## 6. Testing Strategy
Update/add tests for:
1. `publishers/facebook_page.py`
   - Success path for photo publish, text publish, and comment.
   - HTTP error path surfaces meaningful exception.

2. `core/orchestrator.py`
   - Facebook step is invoked after Sheets and before Telegram.
   - When image exists: photo publish attempted.
   - When image missing/fails: text fallback attempted.
   - Comment attempted only when `wp_url` exists.
   - Telegram message includes expected step markers.
   - Facebook failure does not block Telegram send.

3. `core/config_manager.py`
   - Onboarding captures and stores new Facebook fields.

## 7. Risks & Mitigations
- Risk: Facebook Graph API response shape differences.
  - Mitigation: Parse defensively and include raw response snippet in errors.
- Risk: Invalid/expired token.
  - Mitigation: onboarding validation + clear runtime error in Telegram status line.
- Risk: `post_id` availability differs by endpoint response.
  - Mitigation: normalize response handling in publisher methods and fail clearly if missing.

## 8. Acceptance Criteria
- Facebook config fields are asked during onboarding and saved.
- Pipeline includes new Step 5 Facebook before Telegram.
- Facebook post uses caption + image when image available.
- If WordPress URL exists, system comments that URL on the Facebook post.
- Telegram message reports all step statuses with clear `✅/❌/⚪` indicators.
- Pipeline still completes and reports results even when Facebook step fails.
