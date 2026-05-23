# Multi-Account & Web UI - Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffolding the React frontend and implementing the Account Management UI.

**Architecture:** React (Vite) + Tailwind CSS. Use Axios for API communication. Component-based architecture.

**Tech Stack:** React, Vite, Tailwind CSS, Axios, Lucide React (icons).

---

### Task 1: Initialize Vite + React + Tailwind

**Files:**
- Create: `frontend/` (new directory)
- Modify: `pyproject.toml` (maybe just note node/npm requirements)

- [ ] **Step 1: Create Vite project**

Run: `npm create vite@latest frontend -- --template react`

- [ ] **Step 2: Install Tailwind CSS**

Run: `cd frontend && npm install -D tailwindcss postcss autoprefixer && npx tailwindcss init -p`

- [ ] **Step 3: Configure Tailwind**

```javascript
// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

- [ ] **Step 4: Verify scaffolding**

Run: `cd frontend && npm run build` (just to check everything is ok)

- [ ] **Step 5: Commit**

### Task 2: Basic Layout & Navigation

**Files:**
- Create: `frontend/src/components/Layout.jsx`
- Create: `frontend/src/components/Sidebar.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Create Sidebar component**

- [ ] **Step 2: Create Layout component with Sidebar and Header**

- [ ] **Step 3: Setup basic routing (using a simple state or react-router)**

- [ ] **Step 4: Commit**

### Task 3: Account List Page

**Files:**
- Create: `frontend/src/pages/Accounts.jsx`
- Create: `frontend/src/api/client.js`

- [ ] **Step 1: Setup Axios client with base URL pointing to FastAPI**

- [ ] **Step 2: Create Accounts page that fetches and displays list of accounts**

- [ ] **Step 3: Add "Delete" functionality**

- [ ] **Step 4: Commit**

### Task 4: Account Add/Edit Forms

**Files:**
- Create: `frontend/src/components/AccountForm.jsx`

- [ ] **Step 1: Create a modal or form to add/edit accounts**

- [ ] **Step 2: Handle different config fields based on account type (WP, FB, AI...)**

- [ ] **Step 3: Commit**

### Task 5: Connection Testing UI

**Files:**
- Modify: `frontend/src/pages/Accounts.jsx`

- [ ] **Step 1: Add "Test Connection" button to account cards**

- [ ] **Step 2: Show loading state and success/error message**

- [ ] **Step 3: Commit**
