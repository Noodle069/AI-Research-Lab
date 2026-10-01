"""A second copy of the app must not print a link when the port is already taken (the link would
belong to the new copy's key while the OLD copy answers, so the browser would show 'Forbidden')."""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

APP = Path(__file__).resolve().parent.parent


def _start(data_dir, port):
    env = dict(os.environ, BUDGET_DATA_DIR=str(data_dir), BUDGET_PORT=str(port))
    return subprocess.Popen([sys.executable, "-u", "run.py"], cwd=APP, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def test_second_copy_refuses_and_prints_no_link(tmp_path):
    import socket as _s  # test-only: find a free port
    with _s.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    first = _start(data, port)
    try:
        line = ""
        for _ in range(40):
            line = first.stdout.readline()
            if "/enter?t=" in line:
                break
        assert re.search(r"http://127\.0\.0\.1:%d/enter\?t=" % port, line)
        second = _start(data, port)
        out, _ = second.communicate(timeout=30)
        assert second.returncode == 1
        assert "/enter?t=" not in out
        assert "already in use" in out
    finally:
        first.terminate()
        first.wait(timeout=10)
        time.sleep(0.1)
