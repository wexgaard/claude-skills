# Wexgaard Claude Skills

A collection of Claude Code skills for AI-assisted development workflows.

## Installation

### Via Claude Code plugin marketplace (recommended)

Add the marketplace once, then install any plugin listed in
[Available Skills](#available-skills):

```
/plugin marketplace add wexgaard/claude-skills
/plugin install <plugin>@wexgaard-skills
```

Each plugin's skills are invoked as `/<plugin>:<skill>` — see the table
below for the exact pairs (e.g. `/memory-compiler:setup`).

### Manual

Substitute `<plugin>` and `<skill>` with any row from
[Available Skills](#available-skills) (e.g. `memory-compiler` + `setup`).

Bash (macOS / Linux / WSL / Git Bash):

```bash
git clone https://github.com/wexgaard/claude-skills.git
cp -r claude-skills/plugins/<plugin>/skills/<skill> ~/.claude/skills/<plugin>-<skill>
```

PowerShell (Windows):

```powershell
git clone https://github.com/wexgaard/claude-skills.git
Copy-Item -Recurse -Path "claude-skills\plugins\<plugin>\skills\<skill>" -Destination "$env:USERPROFILE\.claude\skills\<plugin>-<skill>"
```

## Available Skills

| Plugin | Skill | Description |
|--------|-------|-------------|
| `memory-compiler` | `setup` | Installer for Cole Medin's Claude Memory Compiler. Asks whether to clone Cole's upstream, a fork, or a custom URL into any project, merges the hooks into the project's Claude Code settings, and updates `.gitignore` to enable automatic session capture and knowledge compilation. |
| `memory-compiler` | `migrate` | Swaps the `origin` of an existing `.memory-compiler/` install to a different memory-compiler repo (upstream ↔ fork, or either ↔ a custom URL), fast-forwards `main`, and re-runs `uv sync`. Aborts cleanly on a dirty tree (e.g. when `show-compile-progress` has patched `flush.py`) with recovery instructions. Local state (`daily/`, `knowledge/`, `state.json`) is gitignored inside the clone and preserved. |
| `memory-compiler` | `show-compile-progress` | Opt-in UI patch for `memory-compiler`'s end-of-day compile. Replaces the empty "claude" popup window with a labelled console that shows a banner, spinner, elapsed time, and live step log; the window closes by itself when the compile finishes. Requires `memory-compiler:setup` to have been run first. |
| `memory-bridge` | `sync` | Forwards `memory-compiler` daily logs to a configurable HTTP ingestion endpoint on each `SessionEnd`, so per-project session knowledge can feed a cross-project memory store. The forwarder is stdlib-only and POSTs JSON with an `X-API-Key` header; the exact payload and endpoint shape are documented in the skill. Also handles rotate-key / reconfigure / status / force-today on re-run. |
| `git` | `commit` | Stage changes and create a conventional commit message generated from the diff. Picks `feat` / `fix` / `refactor` / `chore` / `docs` / `style` / `test` / `perf` based on the change, derives a scope from the affected area, and commits via heredoc so multi-line messages keep their formatting. Refuses to amend published commits or `--no-verify`, and asks before staging anything that looks like a secret (`.env`, credentials). |
| `git` | `commit-push` | Same as `commit`, then pushes to the current remote branch in one step. Auto-invocation is disabled (`disable-model-invocation: true`) — the user must invoke it explicitly. Inherits all `commit` rules, refuses to force-push to `main`/`master`, and stops without pushing if the commit step bailed. |
| `claude-md` | `audit` | Maintenance pass over every `CLAUDE.md` in the project. Flags dead file/symbol references, content duplicated across sibling files, oversized sections (>~50 lines), and outdated patterns. Reports a per-file punch list with ✓/⚠/✗ findings, drafts the exact edits, and applies only what the user approves via `AskUserQuestion`. Does not add new content — that is `session:reflect`'s job. |
| `session` | `reflect` | End-of-session retrospective. Inventories what actually happened (files edited, bugs fixed, decisions made, friction points), categorises each item as a CLAUDE.md edit / new skill / memory entry / nothing, and proposes concrete changes with file paths and exact text. Applies a strict "skill candidacy gate" (frequency + same shape + preloaded-context helps) before proposing any new skill. Skips trivial sessions outright instead of inventing lessons. |
| `skill` | `audit` | Maintenance pass over `~/.claude/skills/`. Across three dimensions: visibility (high-side-effect skills should have `disable-model-invocation: true`; background-knowledge skills should have `user-invocable: false`), determinism (steps that ask the model to do work a script would do better), and composability (logic duplicated across skills that could be a shared helper). Per-skill punch list with ✓/⚠/✗, applies only approved edits. |

## Requirements

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) (Pro, Max, Team, or Enterprise) — required by all plugins
- Git — required by all plugins
- [uv](https://docs.astral.sh/uv/) (Python package manager) — required only by `memory-compiler` (its hooks are Python)

## Credits

- [Cole Medin](https://github.com/coleam00) — [Claude Memory Compiler](https://github.com/coleam00/claude-memory-compiler)