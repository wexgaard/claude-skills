#!/usr/bin/env python3
"""Memory Bridge forwarder for memory-compiler daily logs.

Reads .memory-bridge/config.json and .memory-bridge/.env, then POSTs
.memory-compiler/daily/<day>.md to the configured SecondBrain-compatible
ingest endpoint.

Modes:
  (no args)          Catch up any days between last_forwarded_day and today
                     (exclusive on both ends). Intended to run from SessionEnd.
  --force-today      Forward today's (partial) log as an urgent override.
                     Does not advance the last-forwarded state.
  --connection-test  POST a tiny test article to validate URL + key.
  --status           Print config, last-forwarded day, and log availability.

Stdlib only: no third-party dependencies.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

__version__ = "0.2.0"  # keep in sync with plugins/memory-bridge/.claude-plugin/plugin.json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG_PATH = HERE / "config.json"
ENV_PATH = HERE / ".env"
STATE_PATH = HERE / "last_forwarded_day"
DAILY_DIR = ROOT / ".memory-compiler" / "daily"

_DAY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})$")
_USER_AGENT = f"memory-bridge/{__version__} (+https://github.com/wexgaard/wexgaard-skills)"
_FALLBACK_DAYS = 7


def _today() -> date:
    return date.today()


def die(msg: str, code: int = 1) -> None:
    print(f"memory-bridge: {msg}", file=sys.stderr)
    sys.exit(code)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        die(f"config missing at {CONFIG_PATH}. Run /memory-bridge:sync to install.")
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"config at {CONFIG_PATH} is not valid JSON: {e}")
        return {}


def load_env_file() -> dict:
    env: dict = {}
    if not ENV_PATH.exists():
        return env
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def get_key() -> str:
    key = load_env_file().get("MEMORY_BRIDGE_INGEST_KEY") or os.environ.get(
        "MEMORY_BRIDGE_INGEST_KEY"
    )
    if not key:
        die(
            f"MEMORY_BRIDGE_INGEST_KEY missing. Add it to {ENV_PATH} "
            "or export it in the environment."
        )
    return key  # type: ignore[return-value]


def read_state() -> str | None:
    if not STATE_PATH.exists():
        return None
    text = STATE_PATH.read_text(encoding="utf-8").strip()
    return text or None


def write_state(day: date) -> None:
    STATE_PATH.write_text(day.isoformat() + "\n", encoding="utf-8")


# Kept in lockstep with the shell probe in SKILL.md Step 6. If you change the
# candidate order or the Python-3 sniff here, update the SKILL.md probe too.
def resolve_python_interpreter() -> str | None:
    """Return the first working Python 3 interpreter command on PATH, or None."""
    if shutil.which("python3"):
        return "python3"
    python_path = shutil.which("python")
    if python_path and _is_python3(python_path):
        return "python"
    if shutil.which("py") and _py_launcher_has_python3():
        return "py -3"
    return None


def _is_python3(executable: str) -> bool:
    try:
        out = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    combined = (out.stdout or "") + (out.stderr or "")
    return "Python 3" in combined


def _py_launcher_has_python3() -> bool:
    try:
        out = subprocess.run(
            ["py", "-3", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if out.returncode != 0:
        return False
    combined = (out.stdout or "") + (out.stderr or "")
    return "Python 3" in combined


def _headers_to_dict(headers) -> dict[str, str]:
    if headers is None:
        return {}
    return {str(k).lower(): str(v) for k, v in headers.items()}


def post(url: str, key: str, payload: dict) -> tuple[int, str, dict[str, str]]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": key,
            "User-Agent": _USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return (
                resp.status,
                resp.read().decode("utf-8", errors="replace"),
                _headers_to_dict(resp.headers),
            )
    except urllib.error.HTTPError as e:
        return (
            e.code,
            e.read().decode("utf-8", errors="replace"),
            _headers_to_dict(e.headers),
        )
    except urllib.error.URLError as e:
        die(f"network error reaching {url}: {e.reason}")
        return 0, "", {}  # unreachable


_CF_ERROR_RE = re.compile(r"error code:\s*10\d\d", re.IGNORECASE)


def explain_http_failure(status: int, body: str, headers: dict[str, str]) -> str:
    if status == 403:
        cf_ray = headers.get("cf-ray")
        if cf_ray or _CF_ERROR_RE.search(body) or "cloudflare" in body.lower():
            return (
                "403 from Cloudflare (not the ingest server). Likely causes: "
                "missing/blocked User-Agent, rate limit, or IP reputation. "
                "Check cf-ray in response headers and consult Cloudflare logs. "
                "This is NOT an API-key problem."
            )
        return (
            "403 forbidden: the API key is rejected or the project name does not "
            "match the INGEST_KEY_<PROJECT> env var on the SecondBrain host."
        )
    if status == 422:
        return f"422 unprocessable: payload rejected by SecondBrain. Body: {body}"
    if status == 500:
        return (
            "500 internal: SecondBrain reports no ingest keys configured. "
            "Add INGEST_KEY_<PROJECT>[__<SUBSYSTEM>] to its .env and restart."
        )
    return f"HTTP {status}: {body}"


def build_payload(
    project: str, title: str, content: str, priority: str, tags: list[str]
) -> dict:
    return {
        "title": title,
        "content": content,
        "source_project": project,
        "article_type": "knowledge",
        "priority": priority,
        "tags": tags,
    }


def forward_day(day: date, *, priority: str, title_prefix: str = "") -> int:
    cfg = load_config()
    key = get_key()
    log_path = DAILY_DIR / f"{day.isoformat()}.md"
    if not log_path.exists():
        die(f"no daily log at {log_path}.")
    content = log_path.read_text(encoding="utf-8")
    title = f"{title_prefix}{cfg['project']}: daily log {day.isoformat()}"
    payload = build_payload(
        project=cfg["project"],
        title=title,
        content=content,
        priority=priority,
        tags=["daily-log"],
    )
    status, body, headers = post(cfg["url"], key, payload)
    if status == 200:
        try:
            path = json.loads(body).get("path", "?")
        except json.JSONDecodeError:
            path = "?"
        print(f"memory-bridge: forwarded {day.isoformat()} -> {path}")
        return 0
    print(f"memory-bridge: {explain_http_failure(status, body, headers)}", file=sys.stderr)
    return 1


def list_available_days() -> list[date]:
    if not DAILY_DIR.exists():
        return []
    days: list[date] = []
    for p in DAILY_DIR.iterdir():
        if p.suffix != ".md":
            continue
        m = _DAY_RE.match(p.stem)
        if not m:
            continue
        try:
            days.append(date.fromisoformat(m.group(1)))
        except ValueError:
            continue
    return sorted(days)


def compute_floor(cfg: dict, last: str | None, today: date) -> date:
    if last:
        try:
            return date.fromisoformat(last)
        except ValueError:
            pass
    installed = cfg.get("installed_at")
    if installed:
        try:
            return date.fromisoformat(installed) - timedelta(days=1)
        except ValueError:
            pass
    return today - timedelta(days=_FALLBACK_DAYS)


def cmd_normal() -> int:
    cfg = load_config()
    last = read_state()
    today = _today()
    floor = compute_floor(cfg, last, today)
    candidates = [d for d in list_available_days() if d > floor and d < today]
    if not candidates:
        return 0
    total = len(candidates)
    for i, day in enumerate(candidates, start=1):
        rc = forward_day(day, priority="normal")
        if rc != 0:
            print(
                f"memory-bridge: forwarded {i - 1} of {total} days; "
                f"stopped at {day.isoformat()}",
                file=sys.stderr,
            )
            return rc
        write_state(day)
    return 0


def cmd_force_today() -> int:
    return forward_day(_today(), priority="urgent", title_prefix="[partial] ")


def cmd_connection_test() -> int:
    cfg = load_config()
    key = get_key()
    now = datetime.now().isoformat(timespec="seconds")
    payload = build_payload(
        project=cfg["project"],
        title=f"{cfg['project']}: connection test {now}",
        content=f"SecondBrain connection test from {cfg['project']} at {now}.",
        priority="normal",
        tags=["connection-test"],
    )
    status, body, headers = post(cfg["url"], key, payload)
    if status == 200:
        try:
            path = json.loads(body).get("path", "?")
        except json.JSONDecodeError:
            path = "?"
        print(f"memory-bridge: connection ok -> {path}")
        return 0
    print(f"memory-bridge: {explain_http_failure(status, body, headers)}", file=sys.stderr)
    return 1


def cmd_status() -> int:
    cfg = load_config()
    print(f"url:       {cfg.get('url')}")
    print(f"project:   {cfg.get('project')}")
    print(f"subsystem: {cfg.get('subsystem') or '(none)'}")
    print(f"installed: {cfg.get('installed_at') or '(unknown)'}")
    print(f"last forwarded: {read_state() or '(never)'}")
    today = _today()
    yesterday = (today - timedelta(days=1)).isoformat()
    y_path = DAILY_DIR / f"{yesterday}.md"
    print(f"yesterday log ({yesterday}): {'present' if y_path.exists() else 'missing'}")
    today_s = today.isoformat()
    t_path = DAILY_DIR / f"{today_s}.md"
    print(f"today log ({today_s}):      {'present' if t_path.exists() else 'missing'}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 1:
        return cmd_normal()
    arg = argv[1]
    if arg in ("-h", "--help"):
        print(__doc__)
        return 0
    if arg == "--force-today":
        return cmd_force_today()
    if arg == "--connection-test":
        return cmd_connection_test()
    if arg == "--status":
        return cmd_status()
    die(f"unknown argument: {arg}. Try --help.")
    return 2  # unreachable


if __name__ == "__main__":
    sys.exit(main(sys.argv))
