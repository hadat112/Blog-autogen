# Task 1: Environment Setup

**Goal:** Update dependencies in `pyproject.toml` and install them.

**Files:**
- Modify: `pyproject.toml`

**Instructions:**
1. Update `pyproject.toml` to include `fastapi`, `uvicorn`, `httpx`, and `python-multipart` in the dependencies section.
2. Run `pip install fastapi uvicorn httpx python-multipart` to ensure they are available.
3. Commit the changes to `pyproject.toml`.

**Context:**
This is the first task in setting up a FastAPI backend for the Story Autogen project.

**Testing:**
Verify that `pip show fastapi` returns information after installation.
