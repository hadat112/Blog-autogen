# Multi-Account & Web UI - Phase 1 & 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Setup the database models and refactor the Orchestrator to support multiple accounts.

**Architecture:** Use SQLAlchemy for ORM and SQLite for storage. Refactor the existing `Orchestrator` class to be dependency-injected with account configurations rather than relying on a global config manager.

**Tech Stack:** Python, SQLAlchemy, Pydantic, Pytest.

---

### Task 1: Database Setup and Models

**Files:**
- Create: `core/db.py`
- Create: `core/models.py`
- Test: `tests/test_db_models.py`

- [ ] **Step 1: Create `core/db.py` for engine and session management**

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./story_autogen.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Create `core/models.py` with Account, Pipeline, and Job models**

```python
import uuid
from sqlalchemy import Column, String, JSON, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .db import Base

def generate_uuid():
    return str(uuid.uuid4())

class Account(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # wp, fb, ai, gs, tg
    config = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Pipeline(Base):
    __tablename__ = "pipelines"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # autogen, crawl
    language = Column(String, default="uk")
    step_accounts = Column(JSON, nullable=False)  # e.g. {"wp": "id", "fb": "id"}
    schedule = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, default=generate_uuid)
    pipeline_id = Column(String, ForeignKey("pipelines.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="running")  # running, success, failed
    current_step = Column(String, nullable=True)
    progress = Column(Integer, default=0)
    logs = Column(JSON, default=[])
```

- [ ] **Step 3: Write test to verify DB creation and model persistence**

```python
# tests/test_db_models.py
import pytest
from core.db import Base, engine, SessionLocal
from core.models import Account

def test_create_account():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    acc = Account(name="Test WP", type="wp", config={"url": "http://test.com"})
    db.add(acc)
    db.commit()
    db.refresh(acc)
    assert acc.id is not None
    assert acc.name == "Test WP"
    db.close()
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_db_models.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/db.py core/models.py tests/test_db_models.py
git commit -m "feat: setup database models for accounts and pipelines"
```

### Task 2: Refactor Orchestrator Initialization

**Files:**
- Modify: `core/orchestrator.py`
- Test: `tests/test_orchestrator_refactor.py`

- [ ] **Step 1: Modify `Orchestrator.__init__` to accept explicit configurations**

```python
# core/orchestrator.py
# Change __init__ to accept provider configs directly instead of reading from self.config

class Orchestrator:
    def __init__(self, 
                 ai_config, 
                 wp_config=None, 
                 fb_config=None, 
                 gs_config=None, 
                 tg_config=None,
                 num_threads=5, 
                 limit=None, 
                 language="uk", 
                 debug=False, 
                 disabled_steps=None, 
                 progress_callback=None):
        self.ai_config = ai_config
        self.wp_config = wp_config
        self.fb_config = fb_config
        self.gs_config = gs_config
        self.tg_config = tg_config
        # ... rest of init ...
        
        # Initialize providers using passed configs
        self.ai = NineRouterAI(**ai_config) if ai_config else None
        # ... and so on for wp, fb, sheets ...
```

- [ ] **Step 2: Update provider initialization in `Orchestrator`**

```python
        # In core/orchestrator.py
        self.wp = WordPressPublisher(
            url=wp_config.get("url"),
            username=wp_config.get("username"),
            app_password=wp_config.get("password")
        ) if wp_config else None
```

- [ ] **Step 3: Write test to verify Orchestrator works with injected configs**

```python
# tests/test_orchestrator_refactor.py
from core.orchestrator import Orchestrator

def test_orchestrator_init_with_configs():
    ai_cfg = {"api_key": "test", "text_model": "test", "image_model": "test", "base_url": "http://test"}
    orch = Orchestrator(ai_config=ai_cfg, language="en")
    assert orch.ai is not None
    assert orch.language == "en"
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_orchestrator_refactor.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/orchestrator.py tests/test_orchestrator_refactor.py
git commit -m "refactor: decouple Orchestrator from global config"
```

### Task 3: Account Resolver Utility

**Files:**
- Create: `core/account_resolver.py`
- Test: `tests/test_account_resolver.py`

- [ ] **Step 1: Create utility to fetch account configs from DB by ID**

```python
from sqlalchemy.orm import Session
from .models import Account

def resolve_accounts_for_pipeline(db: Session, step_accounts: dict):
    resolved = {}
    for step, acc_id in step_accounts.items():
        acc = db.query(Account).filter(Account.id == acc_id).first()
        if acc:
            resolved[step] = acc.config
    return resolved
```

- [ ] **Step 2: Write test for account resolver**

```python
# tests/test_account_resolver.py
from core.db import Base, engine, SessionLocal
from core.models import Account
from core.account_resolver import resolve_accounts_for_pipeline

def test_resolve_accounts():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    acc = Account(id="acc-1", name="WP", type="wp", config={"url": "http://wp.com"})
    db.add(acc)
    db.commit()
    
    resolved = resolve_accounts_for_pipeline(db, {"wp": "acc-1"})
    assert resolved["wp"]["url"] == "http://wp.com"
    db.close()
```

- [ ] **Step 3: Run test**

Run: `pytest tests/test_account_resolver.py`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add core/account_resolver.py tests/test_account_resolver.py
git commit -m "feat: add account resolver utility"
```
