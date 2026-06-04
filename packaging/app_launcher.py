import threading
import time
import webbrowser

import uvicorn


def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000")


def main():
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("apps.api.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
