STORY AUTOGEN - WINDOWS QUICK START

For first-time setup:

1. Install Python 3.9 or newer from:
   https://www.python.org/downloads/

   Important: tick "Add Python to PATH" during installation.

2. Double-click install_windows.bat

3. Double-click run.bat

4. The dashboard opens at:
   http://127.0.0.1:8000

Notes:

- Keep the black Story Autogen window open while using the tool.
- Your local data is stored in var/story_autogen.db.
- Add accounts in the Accounts screen.
- Create legacy pipelines in the Pipelines screen.
- Use Rewrite Article, Generate Story, Pattern Library, and WP Publisher from their dedicated sidebar screens.
- Run jobs from the Dashboard screen.
- AI accounts accept any OpenAI-compatible endpoint, API key, and model.
- Sequential AI mode reduces rate-limit pressure; Parallel mode uses the configured concurrency per AI account.
- Before the first database upgrade, a backup is saved under var/backups.
- Pending local images live under var/uploads and are removed after successful publishing or draft cleanup.
- If a draft says publish_unknown, verify WordPress before trying again to avoid duplicate posts.

If the app does not start:

- Re-run install_windows.bat.
- Make sure Python is installed and "Add Python to PATH" was enabled.
- Do not move files out of this folder.
