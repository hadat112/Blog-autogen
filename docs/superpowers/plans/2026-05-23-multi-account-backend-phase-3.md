# Multi-Account & Web UI - Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI backend and Worker Manager to handle accounts, pipelines, and background execution.

**Architecture:** FastAPI REST API with Pydantic for validation. Worker Manager uses `asyncio.create_task` or a similar mechanism to run `Orchestrator` instances in the background.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Uvicorn, Pytest.

---

### Task 1: FastAPI Scaffolding & Schemas

**Files:**
- Create: `api/main.py`
- Create: `api/schemas.py`
- Modify: `pyproject.toml` (add fastapi, uvicorn)
- Test: `tests/test_api_basic.py`

- [ ] **Step 1: Update `pyproject.toml` dependencies**

```toml
# Add to dependencies
dependencies = [
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    # ...
]
```

- [ ] **Step 2: Create `api/schemas.py` for Pydantic models**

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class AccountBase(BaseModel):
    name: string
    type: string
    config: Dict[str, Any]

class AccountCreate(AccountBase):
    pass

class Account(AccountBase):
    id: str
    created_at: datetime
    class Config:
        from_attributes = True

# Similar schemas for Pipeline and Job
```

- [ ] **Step 3: Create basic `api/main.py`**

```python
from fastapi import FastAPI
from core.db import engine, Base

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Story Autogen API")

@app.get("/")
def read_root():
    return {"status": "ok"}
```

- [ ] **Step 4: Write test for API root**

```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 5: Commit**

### Task 2: Account API Endpoints

**Files:**
- Modify: `api/main.py`
- Test: `tests/test_api_accounts.py`

- [ ] **Step 1: Implement GET, POST, PUT, DELETE for Accounts**

```python
@app.post("/accounts", response_model=schemas.Account)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    # ... logic to save to DB ...
```

- [ ] **Step 2: Add connection test endpoint for accounts**

```python
@app.post("/accounts/{account_id}/test")
def test_account_connection(account_id: str, db: Session = Depends(get_db)):
    # ... logic to test WP/FB/AI connection ...
```

- [ ] **Step 3: Commit**

### Task 3: Pipeline API Endpoints

**Files:**
- Modify: `api/main.py`
- Test: `tests/test_api_pipelines.py`

- [ ] **Step 1: Implement CRUD for Pipelines**

- [ ] **Step 2: Commit**

### Task 4: Worker Manager & Background Tasks

**Files:**
- Create: `core/worker_manager.py`
- Modify: `api/main.py`
- Test: `tests/test_worker_manager.py`

- [ ] **Step 1: Create `WorkerManager` singleton**

```python
class WorkerManager:
    def __init__(self):
        self.active_jobs = {} # job_id -> task

    async def start_pipeline_run(self, pipeline_id, db_session):
        # ... logic to resolve accounts, create Orchestrator, and run in background ...
```

- [ ] **Step 2: Implement progress reporting callback**

- [ ] **Step 3: Commit**

### Task 5: Pipeline Execution API

**Files:**
- Modify: `api/main.py`

- [ ] **Step 1: Add `POST /pipelines/{id}/run` endpoint**

- [ ] **Step 2: Add `GET /jobs/active` endpoint**

- [ ] **Step 3: Commit**
