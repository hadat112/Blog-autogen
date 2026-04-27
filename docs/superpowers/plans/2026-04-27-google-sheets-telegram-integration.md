# Google Sheets & Telegram Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Google Sheets logging and Telegram notifications for the story generation workflow.

**Architecture:** Create a `GoogleSheetsProvider` for data persistence and a `send_telegram_msg` helper for notifications. Both will be tested with mocks.

**Tech Stack:** Python, `gspread`, `requests`, `pytest`, `pytest-mock`.

---

### Task 1: Google Sheets Provider

**Files:**
- Create: `providers/google_sheets.py`

- [ ] **Step 1: Implement GoogleSheetsProvider**

```python
import gspread

class GoogleSheetsProvider:
    def __init__(self, credentials_json, sheet_id):
        """
        Setup gspread and open the sheet.
        :param credentials_json: Path to service account JSON file.
        :param sheet_id: ID of the Google Sheet.
        """
        self.gc = gspread.service_account(filename=credentials_json)
        self.sh = self.gc.open_by_key(sheet_id)
        self.wks = self.sh.get_worksheet(0)

    def append_row(self, data_list):
        """
        Appends a row to the first worksheet.
        Expected columns: title, content, caption, image_url, wordpress_url, date_added, status.
        """
        self.wks.append_row(data_list)
```

- [ ] **Step 2: Commit**

```bash
git add providers/google_sheets.py
git commit -m "feat: add GoogleSheetsProvider"
```

---

### Task 2: Telegram Helper

**Files:**
- Create: `utils/helpers.py`

- [ ] **Step 1: Implement send_telegram_msg**

```python
import requests

def send_telegram_msg(token, chat_id, message):
    """
    Sends a message via Telegram Bot API.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()
```

- [ ] **Step 2: Commit**

```bash
git add utils/helpers.py
git commit -m "feat: add telegram helper"
```

---

### Task 3: Integration Tests

**Files:**
- Create: `tests/test_integrations.py`

- [ ] **Step 1: Write tests for GoogleSheetsProvider and Telegram Helper**

```python
import pytest
from unittest.mock import MagicMock, patch
from providers.google_sheets import GoogleSheetsProvider
from utils.helpers import send_telegram_msg

def test_google_sheets_append_row():
    with patch("gspread.service_account") as mock_sa:
        mock_gc = MagicMock()
        mock_sh = MagicMock()
        mock_wks = MagicMock()
        
        mock_sa.return_value = mock_gc
        mock_gc.open_by_key.return_value = mock_sh
        mock_sh.get_worksheet.return_value = mock_wks
        
        provider = GoogleSheetsProvider("fake_creds.json", "fake_sheet_id")
        data = ["Title", "Content", "Caption", "img_url", "wp_url", "2023-10-01", "published"]
        provider.append_row(data)
        
        mock_wks.append_row.assert_called_once_with(data)

def test_send_telegram_msg():
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        token = "fake_token"
        chat_id = "fake_chat_id"
        message = "Hello World"
        
        send_telegram_msg(token, chat_id, message)
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == url
        assert kwargs["json"]["chat_id"] == chat_id
        assert kwargs["json"]["text"] == message
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_integrations.py`
Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add tests/test_integrations.py
git commit -m "test: add integration tests for google sheets and telegram"
```
