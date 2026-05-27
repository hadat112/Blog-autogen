# Multi-Account & Web UI - Phase 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Pipeline management and the real-time Dashboard.

**Architecture:** React components for complex states. Polling for real-time updates.

**Tech Stack:** React, Lucide React, Axios.

---

### Task 1: Pipeline Configuration UI

**Files:**
- Create: `frontend/src/pages/Pipelines.jsx`
- Create: `frontend/src/components/PipelineForm.jsx`

- [ ] **Step 1: Create `Pipelines.jsx` to list existing pipelines**

- [ ] **Step 2: Create `PipelineForm.jsx` (Add/Edit)**
    - Select for Service Accounts (fetching from API).
    - Map each step (AI, WP, FB...) to a specific account.

- [ ] **Step 3: Implement Save/Delete logic for pipelines**

- [ ] **Step 4: Commit**

### Task 2: Dashboard - Quick Run Component

**Files:**
- Create: `frontend/src/pages/Dashboard.jsx`
- Create: `frontend/src/components/QuickRun.jsx`

- [ ] **Step 1: Create `QuickRun.jsx` with input for URL/Prompt and Pipeline selector**

- [ ] **Step 2: Implement "Run" button that triggers the API**

- [ ] **Step 3: Commit**

### Task 3: Dashboard - Active Jobs & Progress

**Files:**
- Modify: `frontend/src/pages/Dashboard.jsx`
- Create: `frontend/src/components/JobCard.jsx`

- [ ] **Step 1: Create `JobCard.jsx` to display progress, current step, and status**

- [ ] **Step 2: Implement polling logic in `Dashboard.jsx` to fetch active jobs every 3 seconds**

- [ ] **Step 3: Commit**

### Task 4: Final Integration

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `api/main.py` (Add CORS if needed)

- [ ] **Step 1: Add CORS middleware to FastAPI if not already present**

- [ ] **Step 2: Update `App.jsx` to use `Dashboard` and `Pipelines` pages**

- [ ] **Step 3: Final Build check**

- [ ] **Step 4: Commit**
