# Design Spec: AI Story Automation Tool

## 1. Overview
An automated system to generate stories, images, and social media captions using AI, then publish them to WordPress and log the results to Google Sheets. The tool is designed to be modular, supporting multiple AI providers and publishing platforms in the future.

## 2. Requirements
- **Input:** A `prompts.txt` file where each line is a base prompt.
- **AI Generation (9router):**
    - Story content and title.
    - Facebook caption (interrupted at a cliffhanger to drive comments/clicks).
    - Image prompt for the next step.
    - Image generation based on the generated image prompt.
- **Publishing:**
    - WordPress REST API: Post title, content, and featured image.
    - Support for both local image upload and direct URL (if supported by WP).
- **Configuration (Onboarding):**
    - Interactive CLI using `questionary` (arrows, enter key).
    - Options to use existing config or overwrite.
    - Ability to update specific config sections.
- **Execution Features:**
    - `--limit`: Max number of stories to generate.
    - `--threads`: Concurrent execution for performance.
    - Multithreading: Each task (story) runs independently.
- **Reporting & Logging:**
    - Google Sheets: Log title, content, caption, image_url, wordpress_url, date_added, status.
    - Telegram: Notify bot upon task completion or error.
    - Console: Real-time status logs for each step.

## 3. Architecture
The system follows a modular "Provider-Publisher" pattern.

### 3.1. Components
- **Core Orchestrator:** Manages the thread pool, reads input, and coordinates between modules.
- **Config Manager:** Handles interactive onboarding and persistent YAML configuration.
- **AI Providers:** Interface for LLM (Text) and Image generation. Implementation: `NineRouterAI`.
- **Publishers:** Interface for content distribution. Implementation: `WordPressPublisher`, Interface-only: `FacebookPublisher`.
- **Loggers/Notifiers:** Google Sheets for database-like logging, Telegram for instant alerts.

### 3.2. Directory Structure
```text
story-autogen/
├── main.py                # CLI entry point
├── config.yaml            # Persistent settings
├── prompts.txt            # Input prompts
├── core/
│   ├── orchestrator.py    # Main logic & multithreading
│   ├── config_manager.py  # questionary-based UI
│   └── logger.py          # Custom logging logic
├── providers/
│   ├── base_ai.py         # AI Interface
│   ├── ai_9router.py      # 9router implementation
│   ├── google_sheets.py   # GSpread integration
│   └── storage.py         # Local/Cloud image handling
├── publishers/
│   ├── base_pub.py        # Publisher Interface
│   └── wp_rest.py         # WordPress REST API implementation
└── utils/
    └── helpers.py         # Shared utilities
```

## 4. Technical Stack
- **Language:** Python 3.10+
- **CLI UI:** `questionary`
- **Network:** `requests`, `httpx`
- **Integration:** `gspread`, `google-auth`, `python-telegram-bot`
- **Configuration:** `pyyaml`
- **Concurrency:** `concurrent.futures.ThreadPoolExecutor`
- **Testing:** `pytest`, `pytest-mock`

## 5. Workflow (per Story)
1. **Fetch Task:** Get prompt from `prompts.txt`.
2. **AI Gen (Text):** Request 9router for story, title, FB caption, image prompt.
3. **AI Gen (Image):** Request 9router for image URL.
4. **Image Prep:** Download locally (if configured) or keep URL.
5. **WP Post:** 
    - Upload image to Media Library.
    - Create post with content and featured image.
6. **Sheet Update:** Append row to Google Sheets.
7. **Telegram Notify:** Send summary to bot.
8. **Final Status:** Log success/failure to console.

## 6. Error Handling
- **Retries:** 3 attempts for all API-based network calls.
- **Isolation:** A failure in one story does not stop other threads.
- **Logging:** Detailed error stack traces saved to `app.log`.

## 7. Future Proofing
- `FacebookPublisher` interface allows adding direct FB posting later.
- `BaseAI` allows swapping 9router for OpenAI, Anthropic, or local LLMs easily.
