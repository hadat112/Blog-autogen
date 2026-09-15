"""End-to-end packaging smoke test.

Creates a temporary virtual environment, installs this project as a package,
starts the packaged launcher, checks GET /, and always cleans up the server
and temporary environment.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]


def find_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def wait_for_http(url: str, process: subprocess.Popen[bytes], timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"server exited early with code {process.returncode}")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status != 200:
                    raise RuntimeError(f"GET / returned HTTP {response.status}")
                return
        except Exception as error:  # Server may still be starting.
            last_error = error
            time.sleep(0.25)
    raise RuntimeError(f"timed out waiting for {url}: {last_error}")


def main() -> int:
    if sys.version_info < (3, 9):
        print("Python 3.9 or newer is required.", file=sys.stderr)
        return 1

    temp_dir = Path(tempfile.mkdtemp(prefix="story-autogen-smoke-"))
    server: subprocess.Popen[bytes] | None = None
    try:
        port = find_free_port()
        venv_dir = temp_dir / ".venv"
        run([sys.executable, "-m", "venv", str(venv_dir)], cwd=ROOT)
        venv_python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

        run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
        run([str(venv_python), "-m", "pip", "install", "--editable", str(ROOT)])
        run(
            [
                str(venv_python),
                "-c",
                "import fastapi, uvicorn, requests, yaml, tqdm, sqlalchemy, multipart",
            ]
        )

        environment = os.environ.copy()
        environment["STORY_AUTOGEN_NO_BROWSER"] = "1"
        environment["STORY_AUTOGEN_PORT"] = str(port)
        environment["STORY_AUTOGEN_DB_URL"] = f"sqlite:///{temp_dir / 'smoke.db'}"
        server = subprocess.Popen(
            [str(venv_python), str(ROOT / "packaging" / "app_launcher.py")],
            cwd=temp_dir,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        wait_for_http(f"http://127.0.0.1:{port}/", server)
        print("Smoke test passed: GET / returned HTTP 200.")
        return 0
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
