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
- **Extensible:** Easily add new publishing adapters (e.g., LinkedIn, Twitter, Medium) by implementing the `BaseStep` interface.

### 🏢 Multi-Account & Multi-Platform
- **WordPress Integration:** Full support for WordPress REST API including media uploads and category management.
- **Facebook Pages:** Automated posting to multiple Facebook pages with custom captioning and image support.
- **Centralized Management:** A modern Web UI to manage multiple accounts, API keys, and job statuses.

### 📊 Business Auditing & Alerts
- **Google Sheets Integration:** Live reporting of every published post (Title, URL, Status, Timestamp) for easy performance tracking.
- **Telegram Notifications:** Real-time alerts sent to your Telegram Bot after each job completion.

---

## 🏗 Architecture

The project follows a clean separation of concerns:

- **Entry Layer:** Supports both an interactive CLI and a FastAPI-powered Web UI.
- **Application Services:** Coordinates database models (SQLAlchemy) and execution logic.
- **Orchestrator:** Manages state, thread-safe concurrency, and the normalized injection of adapters.
- **Pipeline Core:** A sequential runner that executes registered plugins (`core/pipeline/steps/`).
- **Adapter Layer:** Isolates external dependencies (AI Models, Social APIs, Storage) from the business logic.

### System Architecture Flow

```mermaid
graph TD
    subgraph "Entry Layer"
        CLI[Interactive CLI]
        WebUI[React Frontend]
        API[FastAPI Backend]
    end

    subgraph "Core Engine"
        ORC[Orchestrator]
        DB[(SQLite/SQLAlchemy)]
        PL[Pipeline Executor]
    end

    subgraph "Plugins (Steps)"
        P1[AI Content Gen]
        P2[Image Gen]
        P3[WP Publish]
        P4[FB Publish]
        P5[GS Log]
        P6[TG Notify]
    end

    subgraph "External Adapters"
        AI[9Router/OpenAI]
        WP[WordPress REST]
        FB[Meta Graph API]
        GS[Google Sheets API]
        TG[Telegram Bot API]
    end

    %% Flow
    WebUI <--> API
    API <--> DB
    CLI --> ORC
    API --> ORC
    ORC --> PL
    PL --> P1 & P2 & P3 & P4 & P5 & P6

    %% Connections to External
    P1 & P2 --> AI
    P3 --> WP
    P4 --> FB
    P5 --> GS
    P6 --> TG
```

---

## 🛠 Strategic Analysis

### 💪 Strengths
- **High Throughput:** Native multithreading support allows processing hundreds of stories simultaneously.
- **Resilience:** Built-in error handling ensures that one failed API call doesn't stop the entire batch.
- **Hybrid Interface:** Power users can use the CLI for batch automation, while managers use the Web UI for configuration.
- **Clean Codebase:** Type-hinted Python 3 and a modern React 19 frontend with Tailwind CSS 4.

### ⚠️ Considerations (Weaknesses)
- **Configuration Overhead:** Requires several external API integrations (9Router, WordPress, Meta Graph API, Google Cloud, Telegram).
- **Dependency on LLMs:** Quality is highly dependent on the prompt engineering and the stability of the chosen AI provider.
- **Infrastructure:** Requires a stable Python environment and modern Node.js for the frontend suite.

---

## 📦 Getting Started

### Prerequisites
- **Python:** 3.9 or higher
- **Node.js:** 18 or higher (for Web UI)
- **API Keys:** 9Router (or compatible AI provider), Google Cloud (for Sheets), Telegram Bot Token.

### Quick Setup

#### macOS / Linux
```bash
# Clone and run setup
chmod +x setup.sh && ./setup.sh

# Link the runner (Optional)
sudo ln -sf $(pwd)/blog-autogen-runner /usr/local/bin/blog-autogen
```

#### Windows
```powershell
.\setup.bat
```

### Configuration
Run the tool for the first time to launch the interactive onboarding wizard:
```bash
blog-autogen --update
```

## ⚙️ Configuration Details

The system uses a `config.yaml` file to manage integrations. Key configuration groups include:

| Group | Key Fields | Description |
|-------|------------|-------------|
| **AI (9Router)** | `api_key`, `base_url`, `model` | Used for story generation and captioning. |
| **WordPress** | `url`, `username`, `app_password` | Requires "Application Password" for REST API access. |
| **Facebook** | `page_id`, `access_token` | Meta Graph API credentials for page posting. |
| **Google Sheets** | `spreadsheet_id`, `credentials_json` | Service account JSON required for logging. |
| **Telegram** | `bot_token`, `chat_id` | Used for real-time status notifications. |

---

## 📖 Usage Guide

### Mode A: High-Performance CLI
Ideal for batch processing from a `prompts.txt` file.
```bash
# Run with 10 stories and 5 parallel threads
blog-autogen --limit 10 --threads 5

# Process a specific article by URL
blog-autogen --crawl-url "https://example.com/article"
```

### Mode B: Modern Web UI
Ideal for managing accounts and monitoring job progress visually.
```bash
# Start both Backend and Frontend
./dev.sh
```
- **Backend:** `http://localhost:8000`
- **Frontend:** `http://localhost:5173`

---

## 🔧 Troubleshooting

### 1. WordPress "Unauthorized" Error
- **Cause:** Incorrect username or Application Password.
- **Fix:** Ensure you are using a generated **Application Password** (WP Admin > Users > Profile), not your login password.

### 2. Facebook Post Failure
- **Cause:** Expired Page Access Token or insufficient permissions.
- **Fix:** Use the Meta for Developers "Graph API Explorer" to generate a **Permanent Page Access Token** with `pages_manage_posts` and `pages_read_engagement` permissions.

### 3. Google Sheets "Permission Denied"
- **Cause:** Service account email not invited to the spreadsheet.
- **Fix:** Open your Google Sheet, click **Share**, and add the service account email (found in your `credentials.json`) as an **Editor**.

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
pip install -e ".[dev]"
pytest
```

---
*Built with precision for the modern content era.*
