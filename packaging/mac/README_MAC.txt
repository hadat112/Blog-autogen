STORY AUTOGEN - macOS RELEASE GUIDE

This release runs the local dashboard at:
http://127.0.0.1:8000

Requirements
------------

- macOS
- Python 3.9 or newer
- Internet access for the first installation (PyPI downloads)
- A web browser

Install from Finder
-------------------

1. Unzip the versioned StoryAutogen-Mac-v<MAJOR.MINOR.PATCH>.zip. Do not move the
   individual files out of the extracted StoryAutogen-Mac-v<MAJOR.MINOR.PATCH>
   folder.
2. Install Python 3.9+ from https://www.python.org/downloads/macos/ if needed.
3. In Finder, right-click install_mac.command and choose Open.
4. If macOS asks for confirmation, choose Open again.
5. Wait until the installer says "Install complete". It creates or reuses the
   local .venv folder; no sudo or administrator password is needed.
6. Right-click run_mac.command and choose Open.

Run from Terminal to see errors
--------------------------------

Open Terminal, drag the extracted StoryAutogen-Mac-v<MAJOR.MINOR.PATCH> folder into
the Terminal window, press Enter, then run:

  ./install_mac.command
  ./run_mac.command

If macOS says permission is denied, run this once from that folder:

  chmod +x install_mac.command run_mac.command

The Terminal window must remain open while the app is running. Press Ctrl+C to
stop it cleanly. The run script keeps the window open after an error so the
message can be read.

Gatekeeper
----------

Downloaded .command files may be blocked. Do not double-click repeatedly:
right-click the file, choose Open, then confirm Open. If it is still blocked,
open System Settings > Privacy & Security, look for the blocked application
message, choose Allow Anyway, and then right-click the file and choose Open.

Internet or PyPI errors
-----------------------

The installer needs PyPI only to download Python packages. If it reports
"INSTALL FAILED", installation is not complete and the app must not be run.
Check that the Mac can browse the Internet, disable a VPN/proxy temporarily if
appropriate, then run install_mac.command again. A firewall or corporate
network may need to allow pypi.org and files.pythonhosted.org. Do not use sudo.

Port 8000 is already in use
---------------------------

The launcher will show the process using port 8000 and stop without starting a
second server. Close the other local app, or stop its Terminal with Ctrl+C,
then run run_mac.command again. The app intentionally does not switch to a
different port because its documented URL is http://127.0.0.1:8000.

Confirm the app is running
--------------------------

The Terminal should show the URL above and remain open. A browser should open
automatically. You can confirm manually by opening:

  http://127.0.0.1:8000

The Story Autogen dashboard should load. If the browser shows a connection
error, read the Terminal output first and run the installer again if it reports
missing dependencies.

Included application notes
--------------------------

- Local data is stored in var/story_autogen.db.
- Pending local images live under var/uploads.
- Database migration backups are stored under var/backups.
- Configure AI, WordPress, Facebook, and Telegram accounts in the dashboard.

Developer smoke test
--------------------

From the project root, run:

  python3 packaging/smoke_test.py

This creates a temporary clean virtual environment, installs the project,
imports the main dependencies, starts the server, verifies GET / returns HTTP
200, and removes the server and temporary environment afterward.
