# AI Story Automation Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular CLI tool that generates stories/images via 9router, posts to WordPress, and logs to Google Sheets with multithreading support.

**Architecture:** Provider-Publisher pattern for modularity. Each story is a standalone task handled by an Orchestrator using a thread pool. Config is managed via an interactive onboarding CLI.

**Tech Stack:** Python 3.10+, questionary, requests, gspread, pyyaml, python-telegram-bot, concurrent.futures.

---

### Task 1: Project Scaffolding & Environment

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `prompts.txt`

- [ ] **Step 1: Create requirements.txt**
```text
requests
httpx
pyyaml
questionary
gspread
google-auth
python-telegram-bot
tqdm
pytest
pytest-mock
```

- [ ] **Step 2: Initialize directories**
Run: `mkdir -p core providers publishers utils tests docs/superpowers/plans docs/superpowers/specs`

- [ ] **Step 3: Create initial prompts.txt**
```text
Một câu chuyện về chú mèo đi hia ở thành phố hiện đại.
Chuyến phiêu lưu của cậu bé gỗ Pinocchio trong thế giới tương lai.
```

- [ ] **Step 4: Commit**
```bash
git add .
git commit -m "chore: initial project scaffold"
```

---

### Task 2: Configuration Manager (Onboarding UI)

**Files:**
- Create: `core/config_manager.py`
- Test: `tests/test_config_manager.py`

- [ ] **Step 1: Write failing test for config loading**
```python
import os
from core.config_manager import ConfigManager

def test_load_config_empty(tmp_path):
    config_path = tmp_path / "config.yaml"
    cm = ConfigManager(str(config_path))
    assert cm.config == {}
```

- [ ] **Step 2: Run test and verify it fails**
Run: `pytest tests/test_config_manager.py`

- [ ] **Step 3: Implement ConfigManager**
```python
import yaml
import os
import questionary

class ConfigManager:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    def save_config(self):
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f)

    def run_onboarding(self):
        # Interactive questionary logic here
        self.config['9router_api_key'] = questionary.text(
            "Enter 9router API Key:",
            default=self.config.get('9router_api_key', '')
        ).ask()
        # ... repeat for WP, Sheets, etc.
        self.save_config()
```

- [ ] **Step 4: Run test and verify it passes**
Run: `pytest tests/test_config_manager.py`

- [ ] **Step 5: Commit**
```bash
git add core/config_manager.py tests/test_config_manager.py
git commit -m "feat: add config manager and onboarding logic"
```

---

### Task 3: 9router AI Provider (Text & Image)

**Files:**
- Create: `providers/base_ai.py`
- Create: `providers/ai_9router.py`
- Test: `tests/test_ai_9router.py`

- [ ] **Step 1: Define BaseAI interface**
```python
from abc import ABC, abstractmethod

class BaseAI(ABC):
    @abstractmethod
    def generate_story(self, prompt):
        pass

    @abstractmethod
    def generate_image(self, image_prompt):
        pass
```

- [ ] **Step 2: Write failing test for 9router implementation**
```python
from providers.ai_9router import NineRouterAI
import responses

@responses.activate
def test_generate_story_success():
    responses.add(responses.POST, "https://api.9router.ai/v1/chat/completions",
                  json={"choices": [{"message": {"content": "Story content\nTitle: My Story\nCaption: Read more...\nImage Prompt: A cat"}}]}, status=200)
    ai = NineRouterAI(api_key="test")
    res = ai.generate_story("Test prompt")
    assert res['title'] == "My Story"
```

- [ ] **Step 3: Implement NineRouterAI**
Include logic to parse Title, Content, Caption, and Image Prompt from the AI response. Implement `generate_image` using the curl example provided in requirements.

- [ ] **Step 4: Run test and verify it passes**
Run: `pytest tests/test_ai_9router.py`

- [ ] **Step 5: Commit**
```bash
git add providers/base_ai.py providers/ai_9router.py tests/test_ai_9router.py
git commit -m "feat: implement 9router AI provider"
```

---

### Task 4: WordPress Publisher (REST API)

**Files:**
- Create: `publishers/base_pub.py`
- Create: `publishers/wp_rest.py`
- Test: `tests/test_wp_rest.py`

- [ ] **Step 1: Define BasePublisher interface**
```python
from abc import ABC, abstractmethod

class BasePublisher(ABC):
    @abstractmethod
    def publish(self, title, content, image_path_or_url):
        pass
```

- [ ] **Step 2: Write failing test for WP publish**
```python
from publishers.wp_rest import WordPressPublisher

def test_wp_publish_mock(mocker):
    mocker.patch('requests.post', return_value=mocker.Mock(status_code=201, json=lambda: {"link": "https://wp.com/post"}))
    wp = WordPressPublisher(url="https://site.com", user="admin", password="app password")
    url = wp.publish("Title", "Content", "https://img.jpg")
    assert url == "https://wp.com/post"
```

- [ ] **Step 3: Implement WordPressPublisher**
Handle media upload if local path is provided, then create post with featured image.

- [ ] **Step 4: Run test and verify it passes**
Run: `pytest tests/test_wp_rest.py`

- [ ] **Step 5: Commit**
```bash
git add publishers/base_pub.py publishers/wp_rest.py tests/test_wp_rest.py
git commit -m "feat: implement WordPress REST API publisher"
```

---

### Task 5: Google Sheets & Telegram Integration

**Files:**
- Create: `providers/google_sheets.py`
- Create: `utils/helpers.py` (for Telegram)

- [ ] **Step 1: Implement GoogleSheetsProvider**
Use `gspread` to append a row: `[title, content, caption, image_url, wp_url, date, status]`.

- [ ] **Step 2: Implement Telegram notify in utils/helpers.py**
```python
import requests

def send_telegram_msg(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})
```

- [ ] **Step 3: Commit**
```bash
git add providers/google_sheets.py utils/helpers.py
git commit -m "feat: add Google Sheets and Telegram notification"
```

---

### Task 4: Core Orchestrator (Multithreading)

**Files:**
- Create: `core/orchestrator.py`

- [ ] **Step 1: Implement Orchestrator**
Use `ThreadPoolExecutor` to process prompts. Each task follows the flow: AI Text -> AI Image -> (Storage) -> WP -> Sheets -> Telegram.

- [ ] **Step 2: Implement logging and status updates**
Print clear logs to console: `[Thread-1] Generating story...`, `[Thread-1] Posted to WP: ...`

- [ ] **Step 3: Commit**
```bash
git add core/orchestrator.py
git commit -m "feat: implement multithreaded orchestrator"
```

---

### Task 5: CLI Entry Point (main.py)

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement main.py**
Parse arguments (`--limit`, `--threads`).
Initialize `ConfigManager`.
If config missing or `--update` passed, run onboarding.
Initialize `Orchestrator` and run.

- [ ] **Step 2: Commit**
```bash
git add main.py
git commit -m "feat: final CLI entry point"
```
