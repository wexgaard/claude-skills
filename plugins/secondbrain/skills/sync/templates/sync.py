#!/usr/bin/env python3
"""SecondBrain forwarder for memory-compiler daily logs.

Reads .secondbrain/config.json and .secondbrain/.env, then POSTs
.memory-compiler/daily/<day>.md to the configured SecondBrain ingest
endpoint.

Modes:
  (no args)          Forward yesterday's log if not already forwarded.
                     Intended to run from a SessionEnd hook.
  --force-today      Forward today's (partial) log as an urgent override.
                     Does not advance the last-forwarded state.
  --connection-test  POST a tiny test article to validate URL + key.
  --status           Print config, last-forwarded day, and log availability.

Stdlib only: no third-party dependencies.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG_PATH = HERE / "config.json"
ENV_PATH = HERE / ".env"
STATE_PATH = HERE / "last_forwarded_day"
DAILY_DIR = ROOT / ".memory-compiler" / "daily"


def die(msg: str, code: int = 1) -> None:
    print(f"secondbrain: {msg}", file=sys.stderr)
    sys.exit(code)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        die(f"config missing at {CONFIG_PATH}. Run /secondbrain:sync to install.")
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
    key = load_env_file().get("SECONDBRAIN_INGEST_KEY") or os.environ.get(
        "SECONDBRAIN_INGEST_KEY"
    )
    if not key:
        die(
            f"SECONDBRAIN_INGEST_KEY missing. Add it to {ENV_PATH} "
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


def post(url: str, key: str, payload: dict) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "X-API-Key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        die(f"network error reaching {url}: {e.reason}")
        return 0, ""  # unreachable


def explain_http_failure(status: int, body: str) -> str:
    if status == 403:
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
    status, body = post(cfg["url"], key, payload)
    if status == 200:
        try:
            path = json.loads(body).get("path", "?")
        except json.JSONDecodeError:
            path = "?"
        print(f"secondbrain: forwarded {day.isoformat()} -> {path}")
        return 0
    print(f"secondbrain: {explain_http_failure(status, body)}", file=sys.stderr)
    return 1


def cmd_normal() -> int:
    target = date.today() - timedelta(days=1)
    last = read_state()
    if last and last >= target.isoformat():
        return 0
    log_path = DAILY_DIR / f"{target.isoformat()}.md"
    if not log_path.exists():
        return 0
    rc = forward_day(target, priority="normal")
    if rc == 0:
        write_state(target)
    return rc


def cmd_force_today() -> int:
    return forward_day(date.today(), priority="urgent", title_prefix="[partial] ")


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
    status, body = post(cfg["url"], key, payload)
    if status == 200:
        try:
            path = json.loads(body).get("path", "?")
        except json.JSONDecodeError:
            path = "?"
        print(f"secondbrain: connection ok -> {path}")
        return 0
    print(f"secondbrain: {explain_http_failure(status, body)}", file=sys.stderr)
    return 1


def cmd_status() -> int:
    cfg = load_config()
    print(f"url:       {cfg.get('url')}")
    print(f"project:   {cfg.get('project')}")
    print(f"subsystem: {cfg.get('subsystem') or '(none)'}")
    print(f"last forwarded: {read_state() or '(never)'}")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    y_path = DAILY_DIR / f"{yesterday}.md"
    print(f"yesterday log ({yesterday}): {'present' if y_path.exists() else 'missing'}")
    today = date.today().isoformat()
    t_path = DAILY_DIR / f"{today}.md"
    print(f"today log ({today}):      {'present' if t_path.exists() else 'missing'}")
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
