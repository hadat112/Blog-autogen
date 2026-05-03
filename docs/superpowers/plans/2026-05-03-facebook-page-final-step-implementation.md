# Facebook Page Final-Step Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Facebook Page publishing (caption + image if available) as a step before Telegram, with optional WordPress-link comment, and include step-by-step ✅/❌/⚪ status in Telegram.

**Architecture:** Add a dedicated `FacebookPagePublisher` module for Graph API calls and keep orchestration logic in `Orchestrator`. Extend onboarding/config with Facebook Page credentials and Graph version. Update `process_prompt` to run Facebook after Sheets, then compose a structured Telegram summary from per-step statuses.

**Tech Stack:** Python 3.9+, `requests`, `pytest`, `unittest.mock`, existing project providers/publishers.

---

## File Structure Map

- Create: `publishers/facebook_page.py`
  - Responsibility: Facebook Page Graph API integration (post photo/text, comment on post).
- Modify: `core/orchestrator.py`
  - Responsibility: pipeline step ordering and status tracking, integrate Facebook publisher, Telegram status formatting.
- Modify: `core/config_manager.py`
  - Responsibility: onboarding prompts/validation/persistence for Facebook config fields.
- Modify: `tests/test_orchestrator.py`
  - Responsibility: orchestrator flow tests for Facebook step placement, fallback/comment behavior, Telegram status markers.
- Create: `tests/test_facebook_page.py`
  - Responsibility: unit tests for Facebook publisher request/response/error behavior.
- Modify: `tests/test_config_manager.py`
  - Responsibility: onboarding saves Facebook config values.

---

### Task 1: Add Facebook Page publisher with tests (TDD)

**Files:**
- Create: `tests/test_facebook_page.py`
- Create: `publishers/facebook_page.py`

- [ ] **Step 1: Write failing tests for Facebook publisher methods**

```python
# tests/test_facebook_page.py
import pytest
from unittest.mock import patch, MagicMock
from publishers.facebook_page import FacebookPagePublisher


def test_publish_photo_caption_success():
    pub = FacebookPagePublisher("123", "token", "v23.0")

    with patch("publishers.facebook_page.requests.post") as mock_post:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"post_id": "123_456", "id": "456"}
        mock_post.return_value = resp

        post_id = pub.publish_photo_caption("Caption", "https://img.test/a.png")

        assert post_id == "123_456"
        mock_post.assert_called_once()


def test_publish_text_success():
    pub = FacebookPagePublisher("123", "token", "v23.0")

    with patch("publishers.facebook_page.requests.post") as mock_post:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"id": "123_789"}
        mock_post.return_value = resp

        post_id = pub.publish_text("Only caption")
        assert post_id == "123_789"


def test_comment_on_post_success():
    pub = FacebookPagePublisher("123", "token")

    with patch("publishers.facebook_page.requests.post") as mock_post:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"id": "987654"}
        mock_post.return_value = resp

        comment_id = pub.comment_on_post("123_456", "https://wp.url/post")
        assert comment_id == "987654"


def test_publish_photo_caption_http_error_raises():
    pub = FacebookPagePublisher("123", "token")

    with patch("publishers.facebook_page.requests.post") as mock_post:
        resp = MagicMock()
        resp.status_code = 400
        resp.text = "bad request"
        resp.json.return_value = {"error": {"message": "bad request"}}
        mock_post.return_value = resp

        with pytest.raises(Exception) as exc:
            pub.publish_photo_caption("Caption", "https://img.test/a.png")

        assert "Facebook API error" in str(exc.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_facebook_page.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'publishers.facebook_page'`.

- [ ] **Step 3: Implement minimal FacebookPagePublisher**

```python
# publishers/facebook_page.py
import requests


class FacebookPagePublisher:
    def __init__(self, page_id: str, access_token: str, graph_version: str = "v23.0"):
        self.page_id = str(page_id).strip() if page_id else ""
        self.access_token = str(access_token).strip() if access_token else ""
        self.graph_version = graph_version or "v23.0"
        self.base_url = f"https://graph.facebook.com/{self.graph_version}"

    def _post(self, path: str, data: dict) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        payload = {**data, "access_token": self.access_token}
        resp = requests.post(url, data=payload, timeout=30)
        body = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            raise Exception(f"Facebook API error {resp.status_code}: {resp.text[:300]}")
        return body

    def publish_photo_caption(self, caption: str, image_url: str) -> str:
        body = self._post(
            f"{self.page_id}/photos",
            {"url": image_url, "caption": caption, "published": "true"},
        )
        post_id = body.get("post_id") or body.get("id")
        if not post_id:
            raise Exception(f"Facebook API error: missing post id in response {body}")
        return post_id

    def publish_text(self, caption: str) -> str:
        body = self._post(f"{self.page_id}/feed", {"message": caption})
        post_id = body.get("id")
        if not post_id:
            raise Exception(f"Facebook API error: missing post id in response {body}")
        return post_id

    def comment_on_post(self, post_id: str, message: str) -> str:
        body = self._post(f"{post_id}/comments", {"message": message})
        comment_id = body.get("id")
        if not comment_id:
            raise Exception(f"Facebook API error: missing comment id in response {body}")
        return comment_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_facebook_page.py -v`
Expected: PASS all tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_facebook_page.py publishers/facebook_page.py
git commit -m "feat: add Facebook Page publisher for post and comment"
```

---

### Task 2: Extend onboarding/config for Facebook fields (TDD)

**Files:**
- Modify: `tests/test_config_manager.py`
- Modify: `core/config_manager.py`

- [ ] **Step 1: Write failing onboarding persistence test**

```python
# append to tests/test_config_manager.py
from unittest.mock import patch
from core.config_manager import ConfigManager


def test_onboarding_saves_facebook_fields(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    manager = ConfigManager(config_path=str(cfg_file))

    answers = iter([
        "http://localhost:20128/v1",   # ninerouter_base_url
        "key",                         # ninerouter_api_key
        "text-model",                  # ninerouter_text_model
        "image-model",                 # ninerouter_image_model
        "https://wp.example.com",      # wordpress_url
        "wp_user",                     # wordpress_username
        "wp_pass",                     # wordpress_password
        "sheet_id",                    # google_sheets_id
        "creds.json",                  # google_creds_path
        "bot_token",                   # telegram_bot_token
        "chat_id",                     # telegram_chat_id
        "123456789",                   # facebook_page_id
        "EAAB-token",                  # facebook_page_access_token
        "v23.0",                       # facebook_graph_version
        "Direct",                      # image_mode
    ])

    with patch("core.config_manager.questionary.text") as mock_text, \
         patch("core.config_manager.questionary.select") as mock_select, \
         patch("core.config_manager.questionary.confirm") as mock_confirm, \
         patch("core.config_manager.requests.get") as mock_get:
        mock_text.side_effect = [type("A", (), {"ask": lambda self: next(answers)})() for _ in range(12)]
        mock_select.side_effect = [
            type("A", (), {"ask": lambda self: "text-model"})(),
            type("A", (), {"ask": lambda self: "image-model"})(),
            type("A", (), {"ask": lambda self: "Direct"})(),
        ]
        mock_confirm.return_value.ask.return_value = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"result": {"username": "bot"}, "data": []}

        manager.run_onboarding(update=True)

    assert manager.config["facebook_page_id"] == "123456789"
    assert manager.config["facebook_page_access_token"] == "EAAB-token"
    assert manager.config["facebook_graph_version"] == "v23.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_manager.py::test_onboarding_saves_facebook_fields -v`
Expected: FAIL because onboarding does not yet ask/save Facebook keys.

- [ ] **Step 3: Implement onboarding prompts for Facebook config**

```python
# core/config_manager.py (inside run_onboarding, after Telegram and before image_mode)
self.config["facebook_page_id"] = ask_with_validation(
    "Facebook Page ID:",
    "facebook_page_id"
)
self.config["facebook_page_access_token"] = ask_with_validation(
    "Facebook Page Access Token:",
    "facebook_page_access_token"
)
self.config["facebook_graph_version"] = ask_with_validation(
    "Facebook Graph API Version:",
    "facebook_graph_version",
    default_val_override="v23.0"
)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_config_manager.py -v`
Expected: PASS including new Facebook onboarding test.

- [ ] **Step 5: Commit**

```bash
git add tests/test_config_manager.py core/config_manager.py
git commit -m "feat: add Facebook config fields to onboarding"
```

---

### Task 3: Integrate Facebook step into orchestrator before Telegram (TDD)

**Files:**
- Modify: `tests/test_orchestrator.py`
- Modify: `core/orchestrator.py`

- [ ] **Step 1: Write failing orchestrator flow tests for Facebook placement and comment behavior**

```python
# add/adjust in tests/test_orchestrator.py
@patch("core.orchestrator.send_telegram_msg")
@patch("core.orchestrator.FacebookPagePublisher")
@patch("core.orchestrator.NineRouterAI")
@patch("core.orchestrator.GoogleSheetsProvider")
@patch("core.orchestrator.WordPressPublisher")
@patch("core.orchestrator.StorageProvider")
def test_process_prompt_posts_to_facebook_before_telegram(
    mock_storage, mock_wp, mock_sheets, mock_ai, mock_fb_cls, mock_telegram, mock_config
):
    mock_config["facebook_page_id"] = "123"
    mock_config["facebook_page_access_token"] = "token"
    mock_config["facebook_graph_version"] = "v23.0"

    orch = Orchestrator(mock_config)
    orch.ai.generate_story.return_value = {
        "title": "Test Title",
        "content": "Test Content " * 80,
        "caption": "Test Caption " * 20,
        "image_prompt": "Image prompt",
    }
    orch.ai.generate_image.return_value = "https://img.url/a.png"
    orch.wp.publish.return_value = "https://wp.url/story"

    fb = mock_fb_cls.return_value
    fb.publish_photo_caption.return_value = "123_999"
    fb.comment_on_post.return_value = "cmt_1"

    orch.process_prompt("Prompt")

    orch.sheets.append_row.assert_called_once()
    fb.publish_photo_caption.assert_called_once()
    fb.comment_on_post.assert_called_once_with("123_999", "https://wp.url/story")
    mock_telegram.assert_called_once()


@patch("core.orchestrator.send_telegram_msg")
@patch("core.orchestrator.FacebookPagePublisher")
@patch("core.orchestrator.NineRouterAI")
@patch("core.orchestrator.GoogleSheetsProvider")
@patch("core.orchestrator.WordPressPublisher")
@patch("core.orchestrator.StorageProvider")
def test_process_prompt_skips_fb_comment_without_wp_url(
    mock_storage, mock_wp, mock_sheets, mock_ai, mock_fb_cls, mock_telegram, mock_config
):
    mock_config["facebook_page_id"] = "123"
    mock_config["facebook_page_access_token"] = "token"

    orch = Orchestrator(mock_config)
    orch.ai.generate_story.return_value = {
        "title": "Test Title",
        "content": "Test Content " * 80,
        "caption": "Test Caption " * 20,
        "image_prompt": "Image prompt",
    }
    orch.ai.generate_image.return_value = "https://img.url/a.png"
    orch.wp.publish.return_value = ""

    fb = mock_fb_cls.return_value
    fb.publish_photo_caption.return_value = "123_999"

    orch.process_prompt("Prompt")

    fb.publish_photo_caption.assert_called_once()
    fb.comment_on_post.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_orchestrator.py::test_process_prompt_posts_to_facebook_before_telegram tests/test_orchestrator.py::test_process_prompt_skips_fb_comment_without_wp_url -v`
Expected: FAIL because `FacebookPagePublisher` is not yet used in orchestrator.

- [ ] **Step 3: Implement orchestrator Facebook integration and step ordering**

```python
# core/orchestrator.py imports
from publishers.facebook_page import FacebookPagePublisher

# in __init__
self.fb = FacebookPagePublisher(
    page_id=config.get("facebook_page_id"),
    access_token=config.get("facebook_page_access_token"),
    graph_version=config.get("facebook_graph_version", "v23.0"),
)

# in process_prompt state vars
fb_post_id = ""
fb_post_error = ""
fb_comment_error = ""
fb_comment_state = "skipped"

# after Sheets step, before Telegram
if self.config.get("facebook_page_id") and self.config.get("facebook_page_access_token"):
    try:
        if image_url:
            try:
                fb_post_id = self.fb.publish_photo_caption(caption, image_url)
            except Exception:
                fb_post_id = self.fb.publish_text(caption)
        else:
            fb_post_id = self.fb.publish_text(caption)

        if wp_url:
            try:
                self.fb.comment_on_post(fb_post_id, wp_url)
                fb_comment_state = "success"
            except Exception as e:
                fb_comment_state = "error"
                fb_comment_error = str(e)
        else:
            fb_comment_state = "skipped"
    except Exception as e:
        fb_post_error = str(e)
```

- [ ] **Step 4: Update Telegram summary with step markers**

```python
# core/orchestrator.py telegram message block
step_lines = []
step_lines.append("✅ AI text")
step_lines.append("✅ AI image" if not image_error else f"❌ AI image: {image_error[:80]}")
step_lines.append("✅ WordPress" if wp_url else f"❌ WordPress: {error_msg[:80]}")
step_lines.append("✅ Google Sheets")
step_lines.append("✅ Facebook post" if fb_post_id else f"❌ Facebook post: {fb_post_error[:80]}")

if fb_comment_state == "success":
    step_lines.append("✅ FB comment wp_url")
elif fb_comment_state == "error":
    step_lines.append(f"❌ FB comment: {fb_comment_error[:80]}")
else:
    step_lines.append("⚪ FB comment skipped (no wp_url)")

msg = (
    "✅ <b>Story Processed</b>\n\n"
    f"Title: {title}\n"
    + "\n".join(step_lines)
    + f"\n\nWP: {wp_url or 'N/A'}"
    + f"\nFB Post ID: {fb_post_id or 'N/A'}"
)
```

- [ ] **Step 5: Run orchestrator tests**

Run: `pytest tests/test_orchestrator.py -v`
Expected: PASS all orchestrator tests, including new Facebook-related tests.

- [ ] **Step 6: Commit**

```bash
git add core/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add Facebook page publish step before Telegram"
```

---

### Task 4: Add fallback behavior test (image failure → text post) and validate integration

**Files:**
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing fallback test**

```python
@patch("core.orchestrator.send_telegram_msg")
@patch("core.orchestrator.FacebookPagePublisher")
@patch("core.orchestrator.NineRouterAI")
@patch("core.orchestrator.GoogleSheetsProvider")
@patch("core.orchestrator.WordPressPublisher")
@patch("core.orchestrator.StorageProvider")
def test_process_prompt_fallbacks_to_fb_text_post_when_photo_post_fails(
    mock_storage, mock_wp, mock_sheets, mock_ai, mock_fb_cls, mock_telegram, mock_config
):
    mock_config["facebook_page_id"] = "123"
    mock_config["facebook_page_access_token"] = "token"

    orch = Orchestrator(mock_config)
    orch.ai.generate_story.return_value = {
        "title": "Test Title",
        "content": "Test Content " * 80,
        "caption": "Test Caption " * 20,
        "image_prompt": "Image prompt",
    }
    orch.ai.generate_image.return_value = "https://img.url/a.png"
    orch.wp.publish.return_value = "https://wp.url/story"

    fb = mock_fb_cls.return_value
    fb.publish_photo_caption.side_effect = Exception("photo failed")
    fb.publish_text.return_value = "123_777"

    orch.process_prompt("Prompt")

    fb.publish_photo_caption.assert_called_once()
    fb.publish_text.assert_called_once_with("Test Caption " * 20)
```

- [ ] **Step 2: Run fallback test to verify it fails first**

Run: `pytest tests/test_orchestrator.py::test_process_prompt_fallbacks_to_fb_text_post_when_photo_post_fails -v`
Expected: FAIL before fallback implementation is correct.

- [ ] **Step 3: Adjust implementation minimally if needed to satisfy exact fallback behavior**

```python
# core/orchestrator.py (inside facebook step)
if image_url:
    try:
        fb_post_id = self.fb.publish_photo_caption(caption, image_url)
    except Exception as e:
        fb_post_error = str(e)
        fb_post_id = self.fb.publish_text(caption)
else:
    fb_post_id = self.fb.publish_text(caption)
```

- [ ] **Step 4: Run targeted and full tests**

Run:
- `pytest tests/test_orchestrator.py::test_process_prompt_fallbacks_to_fb_text_post_when_photo_post_fails -v`
- `pytest -q`

Expected: Targeted test PASS; full suite PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orchestrator.py core/orchestrator.py
git commit -m "test: cover Facebook text fallback when photo post fails"
```

---

### Task 5: Final verification and sample config migration check

**Files:**
- Modify (if needed): `config.yaml` (local runtime config only, do not commit secrets)

- [ ] **Step 1: Verify onboarding prompt order manually**

Run: `python main.py --update`
Expected: prompts include `Facebook Page ID`, `Facebook Page Access Token`, `Facebook Graph API Version`.

- [ ] **Step 2: Verify Facebook step is before Telegram in logs**

Run: `python main.py --limit 1 --threads 1`
Expected output includes:
- `Step 4: Logging to Google Sheets...`
- `Step 5: Publishing to Facebook...`
- `Step 6: Telegram Notification...`

- [ ] **Step 3: Verify Telegram step markers format**

Expected message contains lines for:
- `AI text`, `AI image`, `WordPress`, `Google Sheets`, `Facebook post`, `FB comment wp_url`
with `✅/❌/⚪` markers.

- [ ] **Step 4: Commit final integration adjustments**

```bash
git add core/config_manager.py core/orchestrator.py publishers/facebook_page.py tests/test_facebook_page.py tests/test_orchestrator.py tests/test_config_manager.py
git commit -m "feat: integrate Facebook Page publishing and step-level Telegram status"
```

---

## Spec Coverage Check

- Facebook config in onboarding/config: covered by **Task 2**.
- Dedicated Facebook module: covered by **Task 1**.
- Facebook step before Telegram: covered by **Task 3**.
- Post to Facebook **Page** with caption + image if available: covered by **Task 1 + Task 3**.
- Optional comment with `wp_url` only when present: covered by **Task 3**.
- Telegram ✅/❌/⚪ per-step format: covered by **Task 3**.
- Non-crashing partial failure behavior: covered by **Task 3 + Task 4**.

## Placeholder/Consistency Check

- No TBD/TODO placeholders.
- Method names consistent across tasks:
  - `publish_photo_caption`, `publish_text`, `comment_on_post`.
- Config keys consistent across tasks:
  - `facebook_page_id`, `facebook_page_access_token`, `facebook_graph_version`.
