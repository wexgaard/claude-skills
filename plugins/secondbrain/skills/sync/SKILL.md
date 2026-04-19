---
name: sync
description: Connects the current project to a SecondBrain ingest endpoint so memory-compiler's daily logs are forwarded as cross-project knowledge. Use this skill when the user says 'sync to second brain', 'connect to second brain', 'forward memory to brain', 'send daily log to brain', 'hook up secondbrain', 'install secondbrain sync', 'setup secondbrain', or wants per-project session memory to feed a personal cross-project brain. Also use for follow-up actions on an existing install — rotating the API key, reconfiguring the URL/project, checking status, or forcing today's log to be forwarded immediately.
---

# SecondBrain Sync

This skill wires the current project into a SecondBrain ingest endpoint: it writes a small forwarder + a `SessionEnd` hook that POSTs each day's `memory-compiler` daily log to the endpoint, so a personal cross-project brain receives a rolling digest of what was happening in every project.

**Relationship to `memory-compiler`:** `secondbrain` consumes `memory-compiler`'s output. The daily log (`.memory-compiler/daily/<YYYY-MM-DD>.md`) is already a day-scoped narrative of every Claude Code session in the project — exactly the right granularity to feed a cross-project brain. Project brains stay deep and narrow; SecondBrain stays broad and shallow. Detail-level knowledge (concepts, connections, Q&A articles) is not forwarded.

**Hard prerequisite:** `memory-compiler` must be installed in the project first. This skill refuses to install otherwise.

## Ingest contract (what the forwarder targets)

- `POST <base>/ingest` with header `X-API-Key: <secret>` and JSON body:
  - `title`, `content`, `source_project` (required)
  - `article_type` (`knowledge` | `decision` | `dependency` | `deadline`; default `knowledge`)
  - `priority` (`normal` | `cross-project` | `urgent`; default `normal`)
  - `tags` (optional list)
- `source_project` must match the `<PROJECT>` half of the env var `INGEST_KEY_<PROJECT>[__<SUBSYSTEM>]=<secret>` that the host operator registered (case-insensitive).
- Success: `200` + `{ "status": "ok", "path": "memory/projects/<project>/YYYY-MM-DD_slug.md" }`.
- Failure codes: `403` (bad key or project mismatch), `422` (bad payload), `500` (no keys configured on host).

The secret must already exist on the SecondBrain host (the operator added `INGEST_KEY_<PROJECT>[__<SUBSYSTEM>]=...` to the host's `.env` and restarted the service). This skill never touches the host — it only wires the client side.

## What this skill does

1. Verifies `.memory-compiler/` exists in the project root.
2. Detects whether `.secondbrain/` already exists. Fresh install vs re-run branches below.
3. On fresh install: collects URL, project name, optional subsystem, and API key. Writes `.secondbrain/config.json`, `.secondbrain/.env`, and `.secondbrain/sync.py`. Appends `.secondbrain/.env` and `.secondbrain/last_forwarded_day` to `.gitignore`. Merges a `SessionEnd` hook into `.claude/settings.json`.
4. Runs a two-phase smoke test: connection check (POST a tiny article) + data availability check (report whether yesterday's log exists).
5. On re-run: offers sync now / force today / rotate key / reconfigure / status.

## Step-by-step instructions

### Step 1: Verify the hard prerequisite

Check whether `.memory-compiler/` exists in the project root.

- If it does not exist, tell the user `secondbrain` has no input to forward without `memory-compiler`. Offer to run `/memory-compiler:setup`, or abort. **Do not** create any `.secondbrain/` files in this state — installing a sync pipeline that cannot function would leave the project in a broken half-configured state.
- If it exists, proceed.

### Step 2: Branch on existing install

Check whether `.secondbrain/config.json` exists.

- If not, go to **Step 3: Fresh install**.
- If yes, go to **Step 7: Re-run menu**.

### Step 3: Collect inputs (fresh install)

Ask the user conversationally — no CLI args — and never invent defaults for the required fields.

1. **Ingest URL** (required, no default). Full URL including `/ingest`, e.g. `https://brain.example.com/ingest`.
2. **Project name** (required). Suggest the basename of the project directory but make the user confirm. Must be alphanumeric + `_`/`-`, 1–100 chars. This becomes `source_project` in the payload and must match the `<PROJECT>` half of the env var registered on the SecondBrain host (case-insensitive).
3. **Subsystem** (optional, default `memory-compiler`). Used only to tell the user which env var name to register on the host (`INGEST_KEY_<PROJECT>__<SUBSYSTEM>`), and stored in config for human-readable status. The user can clear it (then the host env var is simply `INGEST_KEY_<PROJECT>`).
4. **API key** (required). The secret the user already registered on their SecondBrain host.

Before moving on, summarise back to the user: URL, project, subsystem, and which env var they should have registered on the host (`INGEST_KEY_<PROJECT>__<SUBSYSTEM>=<secret>` or bare `INGEST_KEY_<PROJECT>` if subsystem was cleared). Get explicit confirmation to proceed.

### Step 4: Write project files

Create the following under the project root. The templates referenced below live next to this SKILL.md under `templates/`.

- `.secondbrain/config.json` — non-secret JSON:

  ```json
  {
    "url": "<ingest URL>",
    "project": "<project>",
    "subsystem": "<subsystem or empty string>"
  }
  ```

- `.secondbrain/.env` — a single line:

  ```
  SECONDBRAIN_INGEST_KEY=<secret>
  ```

- `.secondbrain/sync.py` — copy verbatim from `templates/sync.py` in this skill directory. Stdlib-only forwarder.

Do not create `.secondbrain/last_forwarded_day` — the forwarder writes it on first successful run.

### Step 5: Update `.gitignore`

Ensure the following lines exist in `.gitignore` at the project root. Append only missing lines; never duplicate.

```
# SecondBrain
.secondbrain/.env
.secondbrain/last_forwarded_day
```

Note: `.secondbrain/config.json` and `.secondbrain/sync.py` are **not** gitignored — they are reproducible non-secret config the user may want to commit.

If `.gitignore` does not exist, create it with just these three lines.

### Step 6: Merge the `SessionEnd` hook

Read the template at `templates/settings.hook.json` in this skill directory. The snippet looks like:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .secondbrain/sync.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Merge into the project's `.claude/settings.json` using the same preserve-and-append pattern `memory-compiler/setup` uses:

- Preserve all existing settings untouched.
- If a `SessionEnd` array already exists (e.g. `memory-compiler` added one), **append** the new entry — do not overwrite and do not replace. Appending places the `secondbrain` hook after `memory-compiler`'s hook, which is the correct order: `memory-compiler` writes the day's log entry first, then `secondbrain` reads the daily tree.
- If the exact same command is already present in the `SessionEnd` array, do not add a duplicate.
- If `.claude/settings.json` does not exist, create it with just the snippet.

> **Note on `python3`:** the template hook uses `python3`. On most Windows installs, `python3` resolves via the py launcher; if the user reports the hook failing with "command not found" on Windows, change it to `python`.

### Step 7: Smoke test (two phases)

**Phase A — connectivity check.** Run the forwarder's connection-test mode from the project root:

```bash
python3 .secondbrain/sync.py --connection-test
```

Interpret the result:

- `secondbrain: connection ok -> <path>` → phase A passes.
- `403 forbidden` → the API key is rejected or `source_project` doesn't match the `<PROJECT>` half of the env var on the host. Surface the exact message and offer to rotate the key or reconfigure the project name. Leave the files in place so the user can fix without re-entering everything.
- `422 unprocessable` → payload issue. Surface the response body and stop.
- `500 internal` → the host has no ingest keys configured. Tell the user to add `INGEST_KEY_<PROJECT>[__<SUBSYSTEM>]=<secret>` to the SecondBrain host's `.env` and restart, then re-run `/secondbrain:sync`.
- `network error` → URL unreachable. Surface the reason and offer to reconfigure the URL.

**Phase B — data availability check.** Check whether `.memory-compiler/daily/<yesterday>.md` exists (yesterday in the user's local date).

- If yes: report that the next `SessionEnd` will forward it.
- If no: explain this is a fresh `memory-compiler` install with no prior day's activity yet. The sync will start forwarding tomorrow onward, once yesterday's log exists. This is expected, not an error.

### Step 8: Report

Summarise:

- Files created/updated.
- `SessionEnd` hook registered (and that it fires *after* `memory-compiler`'s hook).
- Smoke test result.
- Whether yesterday's log is ready to forward.
- Reminder that the current session will not trigger the hook — it activates on the next `SessionEnd`.
- Manual commands the user may find useful: `python3 .secondbrain/sync.py --status`, `--force-today`, `--connection-test`.

## Re-run menu (Step 7 branch)

If `.secondbrain/config.json` already exists when the skill is invoked, load and display the current config (URL, project, subsystem, last-forwarded date) and offer:

1. **Sync now** (default) — run `python3 .secondbrain/sync.py`. Idempotent: if yesterday's log is already forwarded or doesn't exist yet, it no-ops and reports why.
2. **Force today** — run `python3 .secondbrain/sync.py --force-today`. Forwards today's partial log as `priority: urgent` and does **not** advance `last_forwarded_day`, so the normal yesterday-flow will still fire on the next `SessionEnd` after midnight.
3. **Rotate key** — prompt for a new secret, rewrite `.secondbrain/.env`, re-run the phase-A smoke test. If it passes, confirm. If it fails, leave the old key untouched and surface the error.
4. **Reconfigure** — re-collect URL, project, subsystem. Write a new `config.json`. Re-run phase A. Keep the existing key unless the user asks to rotate it too.
5. **Status** — run `python3 .secondbrain/sync.py --status` and print its output.

Never clobber silently. Never duplicate the `.gitignore` lines or the `SessionEnd` hook entry on re-run.

## Timing model (why yesterday, not today)

`memory-compiler`'s `SessionEnd` hook *appends* to today's daily log on every session close, so today's log is incomplete until midnight. If `secondbrain` forwarded today's log on every `SessionEnd`, SecondBrain would either get repeated partial snapshots or one fragment per session. Instead, the normal hook forwards **yesterday's** log on the first `SessionEnd` after yesterday's calendar date has rolled over, using `.secondbrain/last_forwarded_day` to ensure it runs at most once per day.

Result: SecondBrain gets complete daily logs with at most a ~1 day lag, which is the right granularity for cross-project reflection. `--force-today` exists for the "I want today's activity surfaced now" case (e.g. a live briefing) and is explicitly marked `priority: urgent` + title-prefixed `[partial]` so the SecondBrain side can handle it distinctly.

## Notes

- Stdlib-only forwarder. No `uv`, no virtualenv, no third-party Python deps.
- Hook failures inside `SessionEnd` do not block Claude Code. If something is wrong, surface it via `--status` or by running `sync.py` manually.
- The ingest URL and key live entirely on the client side. If the user changes SecondBrain hosts, they `/secondbrain:sync` → **Reconfigure**.
- Secrets policy: `.secondbrain/.env` is gitignored. `.secondbrain/config.json` is not — it contains no secret.
