---
name: sync
description: Bridges memory-compiler daily logs from the current project to a SecondBrain-compatible ingest endpoint so per-project session knowledge feeds a central personal brain. Use this skill when the user says 'set up memory bridge', 'install memory-bridge', 'forward daily logs to brain', 'sync memory compiler to central brain', 'connect project to second brain', 'sync to secondbrain', 'hook up brain ingest', or wants per-project session memory to feed a cross-project brain. Also use for follow-up actions on an existing install — rotating the API key, reconfiguring the URL/project, checking status, or forcing today's log to be forwarded immediately.
---

# Memory Bridge Sync

This skill wires the current project into a SecondBrain-compatible ingest endpoint: it writes a small forwarder + a `SessionEnd` hook that POSTs each day's `memory-compiler` daily log to the endpoint, so a central personal brain receives a rolling digest of what was happening in every project.

**Relationship to `memory-compiler`:** `memory-bridge` consumes `memory-compiler`'s output. The daily log (`.memory-compiler/daily/<YYYY-MM-DD>.md`) is already a day-scoped narrative of every Claude Code session in the project — exactly the right granularity to feed a cross-project brain. Project brains stay deep and narrow; the central brain stays broad and shallow. Detail-level knowledge (concepts, connections, Q&A articles) is not forwarded.

**Hard prerequisite:** `memory-compiler` must be installed in the project first. This skill refuses to install otherwise.

## Ingest contract (what the forwarder targets)

The forwarder speaks the SecondBrain ingest protocol, which any compatible host (self-hosted or otherwise) implements:

- `POST <base>/ingest` with header `X-API-Key: <secret>` and JSON body:
  - `title`, `content`, `source_project` (required)
  - `article_type` (`knowledge` | `decision` | `dependency` | `deadline`; default `knowledge`)
  - `priority` (`normal` | `cross-project` | `urgent`; default `normal`)
  - `tags` (optional list)
- `source_project` must match the `<PROJECT>` half of the env var `INGEST_KEY_<PROJECT>[__<SUBSYSTEM>]=<secret>` that the host operator registered (case-insensitive).
- Success: `200` + `{ "status": "ok", "path": "memory/projects/<project>/YYYY-MM-DD_slug.md" }`.
- Failure codes: `403` (bad key or project mismatch), `422` (bad payload), `500` (no keys configured on host).

The secret must already exist on the ingest host (the operator added `INGEST_KEY_<PROJECT>[__<SUBSYSTEM>]=...` to the host's `.env` and restarted the service). This skill never touches the host — it only wires the client side.

## What this skill does

1. Verifies `.memory-compiler/` exists in the project root.
2. Detects whether `.memory-bridge/` already exists. Fresh install vs re-run branches below.
3. On fresh install: collects project name, URL, API key, and optional subsystem. Writes `.memory-bridge/config.json`, `.memory-bridge/.env`, and `.memory-bridge/sync.py`. Appends `.memory-bridge/.env` and `.memory-bridge/last_forwarded_day` to `.gitignore`. Merges a `SessionEnd` hook into `.claude/settings.json`.
4. Runs a two-phase smoke test: connection check (POST a tiny article) + data availability check (report whether yesterday's log exists).
5. On re-run: offers sync now / force today / rotate key / reconfigure / status.

## Step-by-step instructions

### Step 1: Verify the hard prerequisite

Check whether `.memory-compiler/` exists in the project root.

- If it does not exist, tell the user `memory-bridge` has no input to forward without `memory-compiler`. Offer to run `/memory-compiler:setup`, or abort. **Do not** create any `.memory-bridge/` files in this state — installing a sync pipeline that cannot function would leave the project in a broken half-configured state.
- If it exists, proceed.

### Step 2: Branch on existing install

Check whether `.memory-bridge/config.json` exists.

- If not, go to **Step 3: Fresh install**.
- If yes, go to **Step 7: Re-run menu**.

### Step 3: Collect inputs (fresh install)

Collect the four inputs below **in this order**: project → URL → API key → subsystem. This puts the two free-text prompts (URL, API key) between the two menu prompts, and places the only optional field last.

For each field, use the prompting style specified. Do **not** fall back to conversational free-text for fields marked "AskUserQuestion" — menus exist so the user sees concrete choices rather than having to invent values.

1. **Project name** (required) — use `AskUserQuestion`.
   - Question: "What name should this project use on the ingest host? This becomes `source_project` in the payload and must match the `<PROJECT>` half of the env var registered on the host (case-insensitive)."
   - Options, computed from the project directory basename `<BASENAME>`:
     - `<BASENAME>` — "Use the directory name as-is."
     - Kebab-case of `<BASENAME>` (lowercase, non-alphanumerics collapsed to `-`) — "Use a normalised kebab-case form." Only offer this option if it differs from `<BASENAME>`.
     - `Other` — "Enter a custom name." If selected, validate: alphanumeric + `_`/`-`, 1–100 chars. Re-prompt on invalid input.

2. **Ingest URL** (required) — free-text prompt (URLs are unbounded; a menu can't usefully enumerate them).
   - Prompt: "Full ingest URL including `/ingest`, e.g. `https://brain.example.com/ingest`. No default — paste the URL for your SecondBrain-compatible host."
   - Validate: must be `http://` or `https://` and end in `/ingest` (warn but allow override if the user insists).

3. **API key** (required) — free-text prompt (secret; must not appear in a menu).
   - Prompt: "Paste the API key you registered on the ingest host. It will be written to `.memory-bridge/.env` (gitignored) and never shown again."
   - Do not echo the key in any subsequent summary; refer to it as `<secret>`.

4. **Subsystem** (optional, **default blank**) — use `AskUserQuestion`.
   - Question: "Optional subsystem tag. Only affects the env var name the ingest host needs. Leave blank unless you run multiple forwarders per project."
   - Options:
     - `Leave blank (default)` — "Host env var is `INGEST_KEY_<PROJECT>`. Recommended."
     - `memory-compiler` — "Host env var is `INGEST_KEY_<PROJECT>__MEMORY_COMPILER`. Use only if you have other forwarders for this project."
     - `Other` — "Enter a custom subsystem. Alphanumeric + `_`/`-`."
   - If the user chooses "Leave blank", store `""` in config — do not substitute `memory-compiler`.

**Summary and confirmation.** Before writing any files, summarise back:

- Project: `<project>`
- URL: `<url>`
- API key: `<secret>` (not echoed)
- Subsystem: `<subsystem>` if set, otherwise `(none — bare env var)`
- Env var the host operator must have registered:
  - If subsystem is blank: `INGEST_KEY_<PROJECT>=<secret>` (project uppercased, `-` → `_`).
  - Otherwise: `INGEST_KEY_<PROJECT>__<SUBSYSTEM>=<secret>` (both uppercased, `-` → `_`).

Get explicit confirmation to proceed. If the user rejects, re-open the menu for whichever field they want to change — do not restart the whole flow.

### Step 4: Write project files

Create the following under the project root. The templates referenced below live next to this SKILL.md under `templates/`.

- `.memory-bridge/config.json` — non-secret JSON:

  ```json
  {
    "url": "<ingest URL>",
    "project": "<project>",
    "subsystem": "<subsystem value, or \"\" if the user left it blank>",
    "installed_at": "<YYYY-MM-DD — today's local date, written at setup>"
  }
  ```

  `installed_at` is the floor the forwarder uses on a fresh install to decide how far back to scan for daily logs. Without it, a project with months of `memory-compiler` history would dump all of it into SecondBrain on first `SessionEnd`. See **Timing model → Catch-up behavior** below.

- `.memory-bridge/.env` — a single line:

  ```
  MEMORY_BRIDGE_INGEST_KEY=<secret>
  ```

- `.memory-bridge/sync.py` — copy verbatim from `templates/sync.py` in this skill directory. Stdlib-only forwarder.

Do not create `.memory-bridge/last_forwarded_day` — the forwarder writes it on first successful run.

### Step 5: Update `.gitignore`

Ensure the following lines exist in `.gitignore` at the project root. Append only missing lines; never duplicate.

```
# Memory Bridge
.memory-bridge/.env
.memory-bridge/last_forwarded_day
```

Note: `.memory-bridge/config.json` and `.memory-bridge/sync.py` are **not** gitignored — they are reproducible non-secret config the user may want to commit.

If `.gitignore` does not exist, create it with just these three lines.

### Step 6: Merge the `SessionEnd` hook

**Interpreter probe (run before merging).** The template hook command begins with `python3`, but that literal word is resolved at install time. Probe the user's shell for the first Python 3 interpreter on PATH, in this order:

1. `python3` — check with `command -v python3` (unix-like) or `where python3` (Windows).
2. `python` — resolve the path, then run `python --version` and confirm the output contains `Python 3` (some systems still alias `python` → Python 2).
3. `py -3` — run `py -3 --version` (Windows py launcher).

The first candidate that resolves to a working Python 3 is the resolved interpreter. Substitute its invocation word (including the `-3` flag for the py launcher) into the `command` field of the template below, keeping the ` .memory-bridge/sync.py` suffix intact.

**If no candidate resolves, abort the skill.** Tell the user: *"Python 3 is required for `memory-bridge` — install it from https://www.python.org/downloads/ (or the `python3` package from the Microsoft Store on Windows) and re-run `/memory-bridge:sync`."* Do **not** create any `.memory-bridge/` files in this state; a half-installed pipeline is worse than none. This mirrors Step 1's hard-prerequisite treatment of `memory-compiler`.

> The canonical probe lives in `resolve_python_interpreter()` in `templates/sync.py` and must stay in lockstep with this step. If you change the candidate order or Python-3 sniff in one, change it in both.

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
            "command": "python3 .memory-bridge/sync.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Replace the leading `python3` with the resolved interpreter word from the probe before merging into the project's `.claude/settings.json` using the same preserve-and-append pattern `memory-compiler/setup` uses:

- Preserve all existing settings untouched.
- If a `SessionEnd` array already exists (e.g. `memory-compiler` added one), **append** the new entry — do not overwrite and do not replace. Appending places the `memory-bridge` hook after `memory-compiler`'s hook, which is the correct order: `memory-compiler` writes the day's log entry first, then `memory-bridge` reads the daily tree.
- If the same `sync.py` command is already present in the `SessionEnd` array (regardless of interpreter word), do not add a duplicate.
- If `.claude/settings.json` does not exist, create it with just the snippet (using the resolved interpreter).

### Step 7: Smoke test (two phases)

**Phase A — connectivity check.** Run the forwarder's connection-test mode from the project root:

```bash
python3 .memory-bridge/sync.py --connection-test
```

Interpret the result:

- `memory-bridge: connection ok -> <path>` → phase A passes.
- `403 forbidden` → the API key is rejected or `source_project` doesn't match the `<PROJECT>` half of the env var on the host. Surface the exact message and offer to rotate the key or reconfigure the project name. Leave the files in place so the user can fix without re-entering everything.
- `403 from Cloudflare` (error code 10xx in body, or `cf-ray` header in the response) → Cloudflare blocked the request before it reached the ingest server. **Not** an auth problem. Common causes: missing/blocked User-Agent, rate limit, IP reputation. `memory-bridge` 0.2.0+ sends a descriptive User-Agent; if the block persists, have the user check their Cloudflare logs or contact the host operator. Do **not** offer to rotate the API key.
- `422 unprocessable` → payload issue. Surface the response body and stop.
- `500 internal` → the host has no ingest keys configured. Tell the user to add `INGEST_KEY_<PROJECT>[__<SUBSYSTEM>]=<secret>` to the ingest host's `.env` and restart, then re-run `/memory-bridge:sync`.
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
- Manual commands the user may find useful: `python3 .memory-bridge/sync.py --status`, `--force-today`, `--connection-test`.

## Re-run menu (Step 2 branch)

If `.memory-bridge/config.json` already exists when the skill is invoked, load and display the current config (URL, project, subsystem, last-forwarded date) and offer:

1. **Sync now** (default) — run `python3 .memory-bridge/sync.py`. Idempotent: forwards every completed day between `last_forwarded_day` and today that hasn't been sent yet (see *Timing model → Catch-up behavior*). If there's nothing to do, it exits silently.
2. **Force today** — run `python3 .memory-bridge/sync.py --force-today`. Forwards today's partial log as `priority: urgent` and does **not** advance `last_forwarded_day`, so the normal yesterday-flow will still fire on the next `SessionEnd` after midnight.
3. **Rotate key** — prompt for a new secret, rewrite `.memory-bridge/.env`, re-run the phase-A smoke test. If it passes, confirm. If it fails, leave the old key untouched and surface the error.
4. **Reconfigure** — re-collect project, URL, and subsystem using the same interactive flow as Step 3 (`AskUserQuestion` for project and subsystem, free-text for URL). Pre-populate each menu with a `Keep current: <value>` option as the first choice so accept-as-is is one click. Do **not** re-prompt for the API key here — "Rotate key" (option 3) handles that. Write the new `config.json`, re-run phase A. If phase A fails, leave the old `config.json` in place and surface the error.
5. **Status** — run `python3 .memory-bridge/sync.py --status` and print its output.

Never clobber silently. Never duplicate the `.gitignore` lines or the `SessionEnd` hook entry on re-run.

## Timing model (why yesterday, not today)

`memory-compiler`'s `SessionEnd` hook *appends* to today's daily log on every session close, so today's log is incomplete until midnight. If `memory-bridge` forwarded today's log on every `SessionEnd`, the ingest host would either get repeated partial snapshots or one fragment per session. Instead, the normal hook forwards **completed days only** — everything strictly before today — and uses `.memory-bridge/last_forwarded_day` to ensure each day is forwarded at most once.

Result: the central brain gets complete daily logs with at most a ~1 day lag, which is the right granularity for cross-project reflection. `--force-today` exists for the "I want today's activity surfaced now" case (e.g. a live briefing) and is explicitly marked `priority: urgent` + title-prefixed `[partial]` so the ingest side can handle it distinctly.

### Catch-up behavior

The normal hook does not target a single "yesterday" — it scans `.memory-compiler/daily/` for **every** day whose log file falls between `last_forwarded_day` (exclusive) and today (exclusive), and forwards them in ascending order. After each successful POST, `last_forwarded_day` advances to that day, so a crash or network failure mid-batch resumes cleanly on the next `SessionEnd`. This means weekends, vacations, and other multi-day gaps no longer orphan logs.

On a fresh install with no `last_forwarded_day` yet, the forwarder uses `installed_at` from `config.json` (written during Step 4) as the floor — specifically `installed_at - 1`, so the day before setup is included. If `installed_at` is missing (hand-edited config, or an upgrade from 0.1.0 that never ran successfully), the forwarder defensively caps the backfill to the last 7 days. This prevents a fresh install from dumping months of pre-`memory-bridge` history on first `SessionEnd`.

On a failure mid-batch, the forwarder prints `forwarded N of M days; stopped at <day>` to stderr and exits non-zero, so manual `python .memory-bridge/sync.py` runs propagate the error.

## Notes

- Stdlib-only forwarder. No `uv`, no virtualenv, no third-party Python deps.
- Hook failures inside `SessionEnd` do not block Claude Code. If something is wrong, surface it via `--status` or by running `sync.py` manually.
- The ingest URL and key live entirely on the client side. If the user changes ingest hosts, they `/memory-bridge:sync` → **Reconfigure**.
- Secrets policy: `.memory-bridge/.env` is gitignored. `.memory-bridge/config.json` is not — it contains no secret.
- The command examples in this doc show `python3` for readability; the hook installed into `.claude/settings.json` uses whichever interpreter the Step 6 probe resolved (`python3`, `python`, or `py -3`). If the user runs `sync.py` manually and `python3` is not on their PATH, they should substitute the word the hook uses.
