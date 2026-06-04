# Packaging Guide

Goal: create a simple zip package for non-technical users. End users only need Python, a browser, and an internet connection for the first install. They do not need Node.js or a code editor.

## 1. Build Machine Requirements

Check versions:

```bash
python3 --version
node --version
npm --version
```

Required:

- Python 3.9+
- Node 20.19+ or 22.12+
- npm

If you use `nvm`, run:

```bash
nvm use
```

## 2. Build Windows Release

Run this on your Mac or development machine:

```bash
./packaging/build_windows_release.command
```

Output:

```text
release/StoryAutogen-Windows.zip
```

Send this zip to Windows users.

## 3. Build macOS Release

Run:

```bash
./packaging/build_mac_release.command
```

Output:

```text
release/StoryAutogen-Mac.zip
```

Send this zip to Mac users.

## 4. Windows End-User Steps

User requirements:

- Windows 10 or Windows 11
- Python 3.9+
- Internet connection for first install
- Browser

Steps:

1. Extract `StoryAutogen-Windows.zip`.
2. Double-click `install_windows.bat` once.
3. Double-click `run.bat` to start the app.
4. Keep the black terminal window open.
5. Open `http://127.0.0.1:8000` if the browser does not open automatically.

## 5. macOS End-User Steps

User requirements:

- macOS
- Python 3.9+
- Internet connection for first install
- Browser

Steps:

1. Extract `StoryAutogen-Mac.zip`.
2. Right-click `install_mac.command`, then choose `Open`.
3. Right-click `run_mac.command`, then choose `Open`.
4. Keep the Terminal window open.
5. Open `http://127.0.0.1:8000` if the browser does not open automatically.

## 6. Packaging Files

```text
packaging/
  build_windows_release.command  Builds the Windows zip from Mac/dev machine
  build_mac_release.command      Builds the macOS zip from Mac/dev machine
  app_launcher.py                Starts the backend and opens the browser
  windows/install_windows.bat    Installs dependencies for Windows users
  windows/run.bat                Starts the app for Windows users
  mac/install_mac.command        Installs dependencies for Mac users
  mac/run_mac.command            Starts the app for Mac users
  legacy/                        Old setup scripts, normally not used
```

Notes:

- `build_*.command` files are for the person creating release zips.
- `.bat` files inside `packaging/windows/` are for Windows users after they receive the zip.

## 7. Release Zip Contents

Included:

```text
adapters/
application/
apps/
core/
infrastructure/
frontend/dist/
prompts.txt
pyproject.toml
app_launcher.py
install/run script
user README
```

Excluded:

```text
venv/
.venv/
frontend/node_modules/
tests/
config.yaml
credentials.json
var/story_autogen.db
*.log
```

## 8. Common Issues

Frontend build fails:

```bash
node --version
```

Use Node 20.19+ or 22.12+.

Windows says `python` is not found:

1. Install Python from `https://www.python.org/downloads/`.
2. Enable `Add Python to PATH` during installation.
3. Run `install_windows.bat` again.

macOS blocks a `.command` file:

1. Right-click the file.
2. Choose `Open`.
3. Confirm `Open` again if macOS asks.

Browser does not open automatically:

```text
http://127.0.0.1:8000
```

Port 8000 is already in use:

1. Close any terminal currently running the app.
2. Run the app again.
3. Restart the computer if the issue remains.
