# Story Autogen Packaging Guide

This guide explains how to package Story Autogen for non-technical users on Windows and macOS.

The intended user experience is simple:

1. User downloads a `.zip` file.
2. User extracts it.
3. User runs the install script once.
4. User double-clicks the run script.
5. The dashboard opens in the browser.

No user should need to run `npm`, open the code editor, or understand the project structure.

## Recommended Release Style

Use a bundled source release with:

- Backend Python code.
- Prebuilt frontend in `frontend/dist`.
- One-click install script.
- One-click run script.
- Local SQLite database created automatically in `var/story_autogen.db`.

This keeps the package easy to debug and avoids heavyweight app packaging.

## What The User Gets

### Windows zip

Generated file:

```text
release/StoryAutogen-Windows.zip
```

Inside:

```text
StoryAutogen-Windows/
  adapters/
  application/
  apps/
  core/
  infrastructure/
  frontend/dist/
  prompts.txt
  pyproject.toml
  app_launcher.py
  install_windows.bat
  run.bat
  README_WINDOWS.txt
```

### macOS zip

Generated file:

```text
release/StoryAutogen-Mac.zip
```

Inside:

```text
StoryAutogen-Mac/
  adapters/
  application/
  apps/
  core/
  infrastructure/
  frontend/dist/
  prompts.txt
  pyproject.toml
  app_launcher.py
  install_mac.command
  run_mac.command
  README_MAC.txt
```

## Build Machine Requirements

The person creating the release zip needs:

- Python 3.9 or newer.
- Node.js 20.19 or newer, or Node.js 22.12 or newer.
- npm.
- Git, optional but useful.

Important: Vite currently requires Node 20.19+ or 22.12+. Node 16 will fail during `npm run build`.

Check versions:

```bash
python3 --version
node --version
npm --version
```

If using `nvm`, this repo includes:

```text
.nvmrc
```

Use:

```bash
nvm use
```

## End User Requirements

### Windows user requirements

The user needs:

- Windows 10 or Windows 11.
- Python 3.9 or newer.
- Internet connection during first install.
- Browser such as Chrome, Edge, or Firefox.

Python install instruction for users:

1. Download Python from:
   https://www.python.org/downloads/
2. During install, tick:
   ```text
   Add Python to PATH
   ```
3. Finish install.

The user does not need Node.js.

### macOS user requirements

The user needs:

- macOS.
- Python 3.9 or newer.
- Internet connection during first install.
- Browser such as Safari, Chrome, or Firefox.

Python install instruction for users:

1. Download Python from:
   https://www.python.org/downloads/macos/
2. Install it normally.

The user does not need Node.js.

macOS may block `.command` files the first time. Tell users:

1. Right-click the `.command` file.
2. Click `Open`.
3. Click `Open` again if macOS asks.

## Packaging Folder Layout

Packaging-related files are grouped under:

```text
packaging/
  PACKAGING_GUIDE.md
  app_launcher.py
  build_windows_release.bat
  build_mac_release.command
  windows/
    README_WINDOWS.txt
    install_windows.bat
    run.bat
  mac/
    README_MAC.txt
    install_mac.command
    run_mac.command
  legacy/
    setup.sh
    setup.bat
```

The release zip still places the user-facing files at the top level so non-technical users do not need to open nested folders.

## Build Windows Release

On the build machine:

```bat
packaging\build_windows_release.bat
```

This script:

1. Builds the frontend with `npm run build`.
2. Creates `release/StoryAutogen-Windows/`.
3. Copies only runtime files.
4. Creates `release/StoryAutogen-Windows.zip`.

If the script fails at frontend build, check Node version:

```bash
node --version
```

Use Node 20.19+ or 22.12+.

## Build macOS Release

On the build machine:

```bash
./packaging/build_mac_release.command
```

Or double-click:

```text
packaging/build_mac_release.command
```

This script:

1. Builds the frontend with `npm run build`.
2. Creates `release/StoryAutogen-Mac/`.
3. Copies only runtime files.
4. Sets executable permissions for Mac scripts.
5. Creates `release/StoryAutogen-Mac.zip`.

If the script fails at frontend build, check Node version:

```bash
node --version
```

Use Node 20.19+ or 22.12+.

## Windows User Instructions

Give the user:

```text
StoryAutogen-Windows.zip
```

Tell them:

1. Right-click the zip and choose `Extract All`.
2. Open the extracted folder.
3. Double-click:
   ```text
   install_windows.bat
   ```
4. Wait until install finishes.
5. Double-click:
   ```text
   run.bat
   ```
6. Keep the black window open.
7. The dashboard opens at:
   ```text
   http://127.0.0.1:8000
   ```

If the app does not open:

1. Open browser manually.
2. Go to:
   ```text
   http://127.0.0.1:8000
   ```

## macOS User Instructions

Give the user:

```text
StoryAutogen-Mac.zip
```

Tell them:

1. Double-click the zip to extract it.
2. Open the extracted folder.
3. Right-click:
   ```text
   install_mac.command
   ```
4. Click `Open`.
5. Wait until install finishes.
6. Right-click:
   ```text
   run_mac.command
   ```
7. Click `Open`.
8. Keep the Terminal window open.
9. The dashboard opens at:
   ```text
   http://127.0.0.1:8000
   ```

If the app does not open:

1. Open browser manually.
2. Go to:
   ```text
   http://127.0.0.1:8000
   ```

## First-Time Setup In The App

After opening the dashboard:

1. Go to `Accounts`.
2. Add AI account.
3. Add WordPress account if publishing to WordPress.
4. Add Facebook Page account if publishing to Facebook.
5. Add Google Sheets account if logging is needed.
6. Add Telegram account if notifications are needed.
7. Go to `Pipelines`.
8. Create a pipeline and select the accounts for each step.
9. Go to `Dashboard`.
10. Paste a URL or prompt and click run.

## Local Data

The app stores user data locally:

```text
var/story_autogen.db
```

This includes:

- Accounts.
- Pipelines.
- Job history.
- Job logs.

If the user moves the folder, the data moves with it.

If the user deletes `var/story_autogen.db`, the app starts fresh.

## Files Not Included In Release

Do not include:

```text
venv/
.venv/
frontend/node_modules/
tests/
docs/superpowers/
docs/archive/
config.yaml
credentials.json
var/story_autogen.db
*.log
```

Reasons:

- `venv` and `node_modules` are huge.
- Tests/docs are not needed by end users.
- `config.yaml`, `credentials.json`, and database files may contain private data.
- The app creates a fresh local database automatically.

## Troubleshooting

### Windows: `python` is not recognized

Python is not installed or was installed without PATH.

Fix:

1. Install Python from:
   https://www.python.org/downloads/
2. Tick `Add Python to PATH`.
3. Re-run `install_windows.bat`.

### macOS: command file cannot be opened

macOS Gatekeeper may block downloaded scripts.

Fix:

1. Right-click the `.command` file.
2. Click `Open`.
3. Click `Open` again.

### Dashboard does not open automatically

Open browser manually and go to:

```text
http://127.0.0.1:8000
```

### Port 8000 already in use

Another app is using port 8000.

Simple fix:

1. Close other terminal windows.
2. Restart the computer.
3. Run the app again.

Developer fix:

Change the port in:

```text
app_launcher.py
```

### Install fails due to internet or pip error

The install script downloads Python packages.

Fix:

1. Check internet connection.
2. Re-run install script.
3. If using company network, try another network.

## Developer Notes

The frontend is served by FastAPI from:

```text
frontend/dist
```

The app uses `HashRouter`, so frontend URLs look like:

```text
http://127.0.0.1:8000/#/dashboard
http://127.0.0.1:8000/#/accounts
http://127.0.0.1:8000/#/pipelines
```

This avoids conflicts with API routes such as:

```text
/accounts
/pipelines
/jobs
```

The launcher opens:

```text
http://127.0.0.1:8000
```

The backend entrypoint is:

```text
apps.api.main:app
```

In the source repo, packaging files live in:

```text
packaging/
```

In a release zip, the local launcher is copied to the release root:

```text
app_launcher.py
```
