# Blog Autogen

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Blog Autogen** is an enterprise-grade AI content engine designed to automate the entire lifecycle of digital storytelling. From initial synthesis and image generation to multi-platform publishing and business auditing, it provides a robust "Core-Plugin" pipeline to scale content production with precision.

---

## 📋 Table of Contents
- [🚀 Key Features](#-key-features)
- [🏗 Architecture](#-architecture)
- [🛠 Strategic Analysis](#-strategic-analysis)
- [📦 Getting Started](#-getting-started)
- [🖱 One-Click Install For Non-Technical Users](#-one-click-install-for-non-technical-users)
- [📦 Packaging Releases](#-packaging-releases)
- [⚙️ Configuration](#️-configuration)
- [📖 Usage Guide](#-usage-guide)
- [🔧 Troubleshooting](#-troubleshooting)
- [🗺 Roadmap](#-roadmap)
- [🧪 Development & Testing](#-development--testing)

---

## 🚀 Key Features

### 🤖 AI-Powered Synthesis
- **Dynamic Storytelling:** Generates high-engagement articles and stories based on raw prompts or crawled URLs.
- **Visual Intelligence:** Automated prompt engineering for high-quality image generation (DALL-E/Midjourney style).
- **Social Optimization:** Creates kịch tính (dramatic) captions specifically optimized for Facebook click-through rates.

### 🛠 Modular "Plugin-First" Architecture
- **Flexible Pipeline:** Enable or disable steps (Image Gen, Facebook, WordPress) on the fly.
- **Atomicity:** Each step is independent. A failure in social posting won't roll back a successful WordPress publication.
- **Extensible:** Easily add new publishing integrations (e.g., LinkedIn, Twitter, Medium) by implementing the `BaseStep` interface.

### 🏢 Multi-Account & Multi-Platform
- **WordPress Integration:** Full support for WordPress REST API including media uploads and category management.
- **Facebook Pages:** Automated posting to multiple Facebook pages with custom captioning and image support.
- **Centralized Management:** A modern Web UI to manage multiple accounts, API keys, and job statuses.

### ✍️ Review-First Content Workflows
- **Rewrite Article:** Rework a WordPress reference into a new localized story, then review before publishing.
- **Pattern Library:** Collect themes and narrative structures in local SQLite with independent background analysis.
- **Generate Story:** Let a bounded tool-calling agent choose stored patterns and prepare a reviewable draft.
- **WordPress Publisher:** Compose manual title/content/category/image input and publish to WordPress from one dedicated screen.
- **Safe handoff:** Published Rewrite/Generate items expose caption and link copy actions; manual publishing exposes link only.

### 📊 Alerts
- **Telegram Notifications:** Real-time alerts sent to your Telegram Bot after each job completion.

---

## 🏗 Architecture

The project follows a clean separation of concerns:

- **Entry Layer:** React Web UI backed by FastAPI.
- **Application Services:** Coordinates database models (SQLAlchemy) and execution logic.
- **StoryOrchestrator:** Manages state, thread-safe concurrency, and normalized integration injection.
- **Pipeline Core:** A sequential runner that executes registered plugins (`app/domain/pipeline/steps/`).
- **Adapter Layer:** Isolates external dependencies (AI Models, Social APIs, Storage) from the business logic.

### System Architecture Flow

```mermaid
graph TD
    subgraph "Entry Layer"
        WebUI[React Frontend]
        API[FastAPI Backend]
    end

    subgraph "Core Engine"
        ORC[StoryOrchestrator]
        DB[(SQLite/SQLAlchemy)]
        PL[Pipeline Executor]
    end

    subgraph "Plugins (Steps)"
        P1[AI Content Gen]
        P2[Image Gen]
        P3[WP Publish]
        P4[FB Publish]
        P5[TG Notify]
    end

    subgraph "External Adapters"
        AI[OpenAI-compatible endpoint]
        WP[WordPress REST]
        FB[Meta Graph API]
        TG[Telegram Bot API]
    end

    WebUI <--> API
    API <--> DB
    API --> ORC
    ORC --> PL
    PL --> P1 & P2 & P3 & P4 & P5

    P1 & P2 --> AI
    P3 --> WP
    P4 --> FB
    P5 --> TG
```

---

## 🛠 Strategic Analysis

### 💪 Strengths
- **High Throughput:** Native multithreading support allows processing hundreds of stories simultaneously.
- **Resilience:** Built-in error handling ensures that one failed API call doesn't stop the entire batch.
- **Focused Web Workflow:** Operators manage accounts, pipelines, and job history from one dashboard.
- **Clean Codebase:** Type-hinted Python 3 and a modern React 19 frontend with Tailwind CSS 4.

### ⚠️ Considerations (Weaknesses)
- **Configuration Overhead:** Requires external integrations such as an OpenAI-compatible API endpoint, WordPress, Meta Graph API, and Telegram.
- **Dependency on LLMs:** Quality is highly dependent on the prompt engineering and the stability of the chosen AI provider.
- **Infrastructure:** Requires a stable Python environment and modern Node.js for development builds.

---

## 📦 Getting Started

### Prerequisites
- **Python:** 3.9 or higher
- **uv:** Python package and environment manager for development
- **Node.js:** 20.19+ or 22.12+ for development/building the Web UI
- **API Keys:** An OpenAI-compatible AI provider, plus any publishing integrations you plan to use.

### Quick Setup

#### macOS / Linux
```bash
uv sync --extra dev
cd frontend && pnpm install
cd ..
./dev.sh
```

#### Windows
```powershell
uv sync --extra dev
cd frontend
pnpm install
cd ..
.\dev.bat
```

### Configuration
Start the dashboard and add service accounts from the Accounts screen.

---

## 🖱 One-Click Install For Non-Technical Users

For non-technical users, do not ask them to run Node.js or development commands. Build a release zip and send it to them.

### Windows User Flow

Give the user:

```text
StoryAutogen-Windows.zip
```

They should:

1. Extract the zip.
2. Double-click `install_windows.bat` once.
3. Double-click `run.bat` whenever they want to use the tool.
4. Keep the black terminal window open.
5. Use the dashboard at `http://127.0.0.1:8000`.

Requirements on the user's Windows machine:

- Windows 10 or Windows 11.
- Python 3.9+.
- Browser.
- Internet connection for first install.

### macOS User Flow

Give the user:

```text
StoryAutogen-Mac.zip
```

They should:

1. Extract the zip.
2. Right-click `install_mac.command`, then click `Open`.
3. Right-click `run_mac.command`, then click `Open`.
4. Keep the Terminal window open.
5. Use the dashboard at `http://127.0.0.1:8000`.

Requirements on the user's Mac:

- macOS.
- Python 3.9+.
- Browser.
- Internet connection for first install.

Full details are in:

```text
packaging/PACKAGING_GUIDE.md
```

---

## 📦 Packaging Releases

The release packages include a prebuilt frontend served by FastAPI from:

```text
frontend/dist
```

The user does not need Node.js.

### Build Windows Release

On a build machine with Node 20.19+ or 22.12+:

```bash
./packaging/build_windows_release.command
```

Output:

```text
release/StoryAutogen-Windows.zip
```

### Build macOS Release

On a build machine with Node 20.19+ or 22.12+:

```bash
./packaging/build_mac_release.command
```

Output:

```text
release/StoryAutogen-Mac.zip
```

The detailed packaging checklist is in:

```text
packaging/PACKAGING_GUIDE.md
```

---

## ⚙️ Configuration Details

The Web UI stores accounts, pipelines, and job history in local SQLite. Global translation settings are stored in `config.yaml`.

Local Web UI database:

```text
var/story_autogen.db
```

Key integration groups include:

| Group | Key Fields | Description |
|-------|------------|-------------|
| **AI Provider** | `api_key`, `base_url`, `text_model`, optional fallback/image models | Any OpenAI-compatible endpoint used for generation and localization. |
| **WordPress** | `url`, `username`, `app_password` | Requires "Application Password" for REST API access. |
| **Facebook** | `page_id`, `access_token` | Meta Graph API credentials for page posting. |
| **Telegram** | `bot_token`, `chat_id` | Used for real-time status notifications. |

---

## 📖 Usage Guide

### Web UI
Use the dashboard to manage accounts, configure legacy pipelines, run prompts/URLs, and monitor every job. Dedicated sidebar screens own Rewrite, Generate Story, Pattern Library, and manual WordPress publishing profiles and drafts.
```bash
# Start both Backend and Frontend in development
./dev.sh
```
- **Backend:** `http://localhost:8000`
- **Frontend:** `http://localhost:5173`

### AI concurrency and recovery

- `translation_mode=sequential` admits one AI request per AI account.
- `translation_mode=parallel` admits up to `translation_max_concurrency` requests per account; background Pattern Analysis has lower priority.
- New Rewrite, Pattern Analysis, and Generate Story calls make one attempt and never silently switch models.
- Before the first schema upgrade, file-based SQLite installs create a timestamped backup under `var/backups/`.
- A `publish_unknown` draft means WordPress may have created the post after a timeout. Verify WordPress before attempting any manual reconciliation; the app does not automatically retry and risk a duplicate.

### Mode C: Packaged Local Web App
Ideal for non-technical users.

```text
run.bat              Windows
run_mac.command      macOS
```

The packaged dashboard opens at:

```text
http://127.0.0.1:8000
```

---

## 🔧 Troubleshooting

### 1. WordPress "Unauthorized" Error
- **Cause:** Incorrect username or Application Password.
- **Fix:** Ensure you are using a generated **Application Password** (WP Admin > Users > Profile), not your login password.

### 2. Facebook Post Failure
- **Cause:** Expired Page Access Token or insufficient permissions.
- **Fix:** Use the Meta for Developers "Graph API Explorer" to generate a Page Access Token with `pages_manage_posts` and `pages_read_engagement` permissions.

### 3. Frontend Build Fails
- **Cause:** Node.js is too old.
- **Fix:** Use Node 20.19+ or 22.12+. This repo includes `.nvmrc`.

### 4. Windows Cannot Find Python
- **Cause:** Python is missing or was installed without PATH.
- **Fix:** Install Python 3.9+ and tick **Add Python to PATH**.

### 5. macOS Blocks `.command` Files
- **Cause:** Gatekeeper blocks downloaded command files.
- **Fix:** Right-click the command file, click **Open**, then confirm.

---

## 🗺 Roadmap
- [ ] **Multi-Language Support:** Expand beyond English and Vietnamese.
- [ ] **Scheduler Integration:** Native cron-style job scheduling within the Web UI.
- [ ] **Advanced Video Prompts:** Generate prompts for video creation tools (Runway/Luma).
- [ ] **New Adapters:** Support for LinkedIn, Medium, and Ghost CMS.

---

## 🧪 Development & Testing

Contributions are welcome! To set up the development environment:
```bash
uv sync --extra dev
uv run pytest
```

Run the backend and frontend dev servers together:

```bash
./dev.sh
```

Frontend type check:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit
```

Frontend build:

```bash
cd frontend
pnpm build
```

Mocked browser journeys (no production AI or WordPress calls):

```bash
cd frontend
pnpm test:e2e:install  # first run only
pnpm test:e2e
```

---
*Built with precision for the modern content era.*
