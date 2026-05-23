# Design Spec: Story Autogen Multi-Account & Web UI

**Date:** 2026-05-23
**Status:** Draft
**Topic:** Multi-account support, Multi-threading, React Web UI, Pipeline Management

## 1. Overview
The current "story-autogen" tool is limited to a single WordPress account and a single language, managed via a CLI and a static `config.yaml`. The goal is to transform this into a multi-account, multi-pipeline platform with a real-time Web UI, capable of running multiple tasks asynchronously in the background.

## 2. Architecture
The system will adopt a Client-Server architecture:
- **Backend:** FastAPI (Python)
    - Manages accounts and pipelines in a SQLite database.
    - Orchestrates background tasks using an internal Worker Manager.
    - Provides a REST API and WebSockets for real-time updates.
- **Frontend:** React (TypeScript/JavaScript) + Tailwind CSS
    - Provides a dashboard for monitoring runs.
    - Includes management pages for accounts and pipeline configurations.
- **Database:** SQLite
    - Stores credentials, pipeline definitions, and execution logs.

## 3. Data Model

### Accounts
Stores credentials for various services.
- `id`: UUID
- `name`: string (e.g., "Main Blog", "English FB Page")
- `type`: enum (WordPress, Facebook, AI_9Router, GoogleSheets, Telegram)
- `config`: JSON (stores API keys, URLs, passwords)

### Pipelines
Defines a sequence of steps and their associated accounts.
- `id`: UUID
- `name`: string
- `type`: enum (Autogen, Crawl)
- `language`: string (e.g., "uk", "vi", "en")
- `step_accounts`: JSON mapping (e.g., `{"wordpress": "uuid-1", "facebook": "uuid-2"}`)
- `schedule`: Cron expression (optional)
- `is_active`: boolean

### Jobs (Execution Logs)
Tracks the progress of a pipeline run.
- `id`: UUID
- `pipeline_id`: UUID
- `start_time`: datetime
- `end_time`: datetime (nullable)
- `status`: enum (Running, Success, Failed)
- `current_step`: string
- `progress`: integer (0-100)
- `logs`: text/JSON

### Quick Run / Link Input
A dedicated component on the Dashboard to trigger pipelines manually with dynamic input.
- **Input Field:** For pasting a URL (Crawl type) or a Prompt (Autogen type).
- **Pipeline Selector:** To choose which configuration (accounts, language) to use for this run.
- **Continuous Mode:** Ability to paste multiple links/prompts or a batch, which will be queued and executed sequentially or in parallel based on the concurrency limit.

## 4. Key Components

### Worker Manager (Backend)
- A singleton service that maintains a pool of active workers.
- Limits global concurrency (configurable).
- Emits progress events via a message bus (or directly to WebSocket manager).

### Refactored Orchestrator
- Decoupled from `config.yaml`.
- Accepts an `Account` objects or configuration dictionaries for each step.
- Supports progress callbacks to report status back to the Worker Manager.

### Real-time Dashboard (Frontend)
- Shows active jobs with progress bars.
- Displays recent activity and success/failure rates.
- Allows manual triggering of pipelines.

## 5. Security
- API keys and passwords will be stored in the SQLite DB.
- Future enhancement: Encrypt sensitive fields at rest.

## 6. Testing Strategy
- **Unit Tests:** For the new Data Model and API endpoints.
- **Integration Tests:** Verifying that a pipeline can correctly use credentials from the DB to complete a full run.
- **UI Tests:** Basic verification of the React components.

## 7. Migration Plan
- Existing `config.yaml` will be imported into the new SQLite DB as the "Default" account and pipeline during the first run.
- The CLI will be kept as a wrapper that can either run a local server or trigger a pipeline via the API.
