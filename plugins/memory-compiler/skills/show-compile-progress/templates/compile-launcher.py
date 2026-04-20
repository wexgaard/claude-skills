"""
Compile launcher - wraps compile.py with a visible, informative console.

Spawned by flush.py's maybe_trigger_compilation() in place of compile.py itself
once the show-compile-progress skill has been applied. Renders a banner,
spinner, and live step log into the console window so the end-of-day compile
is transparent instead of an empty popup.

The child process (compile.py) still writes its full output to compile.log
via a tee, so nothing is lost for post-hoc review. The window auto-closes on
exit; there is no keypress-to-close prompt.
"""

from __future__ import annotations

import itertools
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
COMPILE_SCRIPT = SCRIPTS_DIR / "compile.py"
LOG_FILE = SCRIPTS_DIR / "compile.log"

SPINNER_FRAMES = "|/-\\"
BAR = "=" * 60


def _enable_utf8_console() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass


def _print_banner() -> None:
    print(BAR)
    print("  Memory Compiler - compiling today's daily log")
    print(f"  started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(BAR)
    print()


def _spin(stop_event: threading.Event, start_time: float) -> None:
    frames = itertools.cycle(SPINNER_FRAMES)
    while not stop_event.is_set():
        elapsed = time.monotonic() - start_time
        frame = next(frames)
        sys.stdout.write(f"\r  [{frame}] working... {elapsed:5.1f}s ")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()


def _stream_child_output(proc: subprocess.Popen, log_handle) -> None:
    assert proc.stdout is not None
    for raw in proc.stdout:
        log_handle.write(raw)
        log_handle.flush()
        line = raw.rstrip()
        if not line:
            continue
        sys.stdout.write("\r" + " " * 50 + "\r")
        sys.stdout.write(f"  > {line}\n")
        sys.stdout.flush()


def main() -> int:
    _enable_utf8_console()

    if not COMPILE_SCRIPT.exists():
        print(f"ERROR: compile.py not found at {COMPILE_SCRIPT}", file=sys.stderr)
        return 2

    _print_banner()

    cmd = ["uv", "run", "--directory", str(ROOT), "python", str(COMPILE_SCRIPT)]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"

    start = time.monotonic()
    stop_event = threading.Event()
    spin_thread = threading.Thread(target=_spin, args=(stop_event, start), daemon=True)
    spin_thread.start()

    rc = 1
    try:
        with open(LOG_FILE, "a", encoding="utf-8", newline="") as log_handle:
            log_handle.write(
                f"\n--- compile-launcher started {datetime.now().isoformat()} ---\n"
            )
            log_handle.flush()
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(ROOT),
                env=env,
                bufsize=1,
            )
            stream_thread = threading.Thread(
                target=_stream_child_output, args=(proc, log_handle), daemon=True
            )
            stream_thread.start()
            rc = proc.wait()
            stream_thread.join(timeout=2.0)
    finally:
        stop_event.set()
        spin_thread.join(timeout=1.0)

    duration = time.monotonic() - start
    print()
    print(BAR)
    if rc == 0:
        print(f"  [ok] compile complete in {duration:.1f}s")
    else:
        print(f"  [err] compile failed (exit {rc}) after {duration:.1f}s")
        print(f"        see {LOG_FILE} for details")
    print(BAR)
    return rc


if __name__ == "__main__":
    sys.exit(main())
