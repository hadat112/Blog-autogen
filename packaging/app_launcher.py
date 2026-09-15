import os
import subprocess
import threading
import time
import webbrowser

import uvicorn


def open_browser():
    time.sleep(1.5)
    if os.environ.get("STORY_AUTOGEN_NO_BROWSER") == "1":
        return

    port = os.environ.get("STORY_AUTOGEN_PORT", "8000")
    url = f"http://127.0.0.1:{port}"
    if os.name == "posix" and os.uname().sysname == "Darwin":
        subprocess.run(["open", url], check=False)
    else:
        webbrowser.open(url)


def main():
    threading.Thread(target=open_browser, daemon=True).start()
    port = int(os.environ.get("STORY_AUTOGEN_PORT", "8000"))
    uvicorn.run("app.api.main:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
