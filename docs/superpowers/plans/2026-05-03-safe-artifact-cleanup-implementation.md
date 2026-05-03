# Safe Artifact Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove cache artifacts safely, keep runtime stable, and prevent cache churn from reappearing in git.

**Architecture:** Keep implementation strictly operational: no business-logic changes, only repository hygiene and verification. Use existing ignore rules, remove generated artifacts from disk and git index if needed, then verify with git status and targeted tests. Preserve `venv/` completely to avoid disrupting current execution flow.

**Tech Stack:** Git, Python project structure, pytest.

---

## File Structure Map

- Modify: `.gitignore`
  - Responsibility: ensure ignore coverage for generated caches (`__pycache__/`, `*.py[cod]`, `.pytest_cache/`).
- No source-code logic file modifications required for cleanup itself.
- Verify using existing tests:
  - `tests/test_orchestrator.py`
  - `tests/test_main.py`

---

### Task 1: Lock ignore rules for cache artifacts (TDD-style verification)

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Write a failing check command by asserting required ignore patterns exist**

Run:
```bash
grep -nE '^__pycache__/$|^\*\.py\[cod\]$|^\.pytest_cache/$' .gitignore
```
Expected (RED): If any required line is missing, output does not include all 3 patterns.

- [ ] **Step 2: Run check to verify current state (RED if incomplete)**

Run:
```bash
grep -nE '^__pycache__/$|^\*\.py\[cod\]$|^\.pytest_cache/$' .gitignore
```
Expected: Show all 3 rules. If any missing, treat as failing check.

- [ ] **Step 3: Apply minimal `.gitignore` change if needed**

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
```

- [ ] **Step 4: Re-run check (GREEN)**

Run:
```bash
grep -nE '^__pycache__/$|^\*\.py\[cod\]$|^\.pytest_cache/$' .gitignore
```
Expected: All 3 lines present.

- [ ] **Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: enforce ignore rules for python cache artifacts"
```

---

### Task 2: Remove generated cache artifacts from working tree safely

**Files:**
- Delete generated artifacts only (no source files)

- [ ] **Step 1: Write failing inventory command (RED)**

Run:
```bash
python3 - <<'PY'
import pathlib
root = pathlib.Path('.')
paths = list(root.rglob('__pycache__')) + list(root.rglob('*.pyc')) + [p for p in [root/'.pytest_cache'] if p.exists()]
print(len(paths))
for p in paths[:20]:
    print(p)
PY
```
Expected: Count > 0 (there are artifacts to clean).

- [ ] **Step 2: Remove cache artifacts while preserving `venv/`**

Run:
```bash
python3 - <<'PY'
import shutil, pathlib
root = pathlib.Path('.')
for p in root.rglob('__pycache__'):
    if 'venv' in p.parts:
        continue
    shutil.rmtree(p, ignore_errors=True)
for p in root.rglob('*.pyc'):
    if 'venv' in p.parts:
        continue
    try:
        p.unlink()
    except FileNotFoundError:
        pass
pc = root/'.pytest_cache'
if pc.exists():
    shutil.rmtree(pc, ignore_errors=True)
PY
```

- [ ] **Step 3: Re-run inventory command (GREEN)**

Run:
```bash
python3 - <<'PY'
import pathlib
root = pathlib.Path('.')
paths = [p for p in root.rglob('__pycache__') if 'venv' not in p.parts]
paths += [p for p in root.rglob('*.pyc') if 'venv' not in p.parts]
if (root/'.pytest_cache').exists():
    paths.append(root/'.pytest_cache')
print(len(paths))
PY
```
Expected: `0`.

- [ ] **Step 4: Commit**

```bash
git add -u
git commit -m "chore: remove generated cache artifacts from repository tree"
```

---

### Task 3: Untrack any cache artifacts still in git index

**Files:**
- Git index only

- [ ] **Step 1: Write failing index check (RED if tracked entries exist)**

Run:
```bash
git ls-files | grep -E '__pycache__/|\.pyc$|^\.pytest_cache/'
```
Expected: Any output means cleanup incomplete.

- [ ] **Step 2: Remove tracked cache entries from index if output exists**

Run:
```bash
git ls-files | grep -E '__pycache__/|\.pyc$|^\.pytest_cache/' | xargs -r git rm --cached
```

- [ ] **Step 3: Re-run index check (GREEN)**

Run:
```bash
git ls-files | grep -E '__pycache__/|\.pyc$|^\.pytest_cache/'
```
Expected: No output.

- [ ] **Step 4: Commit**

```bash
git add -u
git commit -m "chore: stop tracking python cache artifacts"
```

---

### Task 4: Verify runtime safety and no regressions

**Files:**
- Test only, no file edits required unless failures found

- [ ] **Step 1: Run targeted regression tests**

Run:
```bash
pytest tests/test_orchestrator.py tests/test_main.py -q
```
Expected: All pass.

- [ ] **Step 2: Verify clean status excludes cache churn**

Run:
```bash
git status --short
```
Expected: No cache artifact changes shown.

- [ ] **Step 3: Optional CLI smoke check**

Run:
```bash
python3 main.py --help
```
Expected: CLI usage output appears without runtime error.

- [ ] **Step 4: Commit any final adjustments**

```bash
git add -u
git commit -m "chore: finalize safe cleanup verification"
```
(Only if there are real final changes.)

---

## Spec Coverage Check

- Remove generated caches safely: Task 2.
- Keep `venv/` intact: Task 2 explicitly excludes `venv` paths.
- Ensure ignore rules are correct: Task 1.
- Untrack lingering cache files: Task 3.
- Validate no flow breakage: Task 4.

## Placeholder/Consistency Check

- No TODO/TBD placeholders.
- Exact paths and commands provided.
- Scope constrained to safe artifact cleanup (no functional refactor).
