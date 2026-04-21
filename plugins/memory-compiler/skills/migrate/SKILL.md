---
name: migrate
description: Swap the `origin` remote of an existing `.memory-compiler/` install in the current project to a different memory-compiler repository (e.g. upstream → fork, fork → upstream, or either → a custom URL), then fast-forward and re-sync. Use when the user says things like "migrate memory-compiler", "switch memory-compiler to the fork", "point memory-compiler at a different repo", "swap memory-compiler origin", or otherwise wants an already-installed memory-compiler to track a new source.
---

# Memory Compiler Migrate

This skill migrates an existing `.memory-compiler/` install in the current project to a different source repository. It preserves all local state (daily logs, knowledge articles, state.json) because those paths are gitignored inside the clone — a fast-forward pull does not touch them.

**Note for agents executing this skill:** bash cwd behavior differs across harnesses. Always use absolute paths and prefer commands like `git -C <path>` and `uv sync --directory <path>` over `cd <path> && ...`.

## What this skill does

1. Resolves the absolute project-root path and verifies `.memory-compiler/` is a git clone.
2. Asks the user which repo to migrate to (upstream, Wexgaard fork, or a pasted URL).
3. Exits early if the install already tracks the chosen repo (but still refreshes).
4. Aborts cleanly if the working tree is dirty (e.g. `show-compile-progress` has patched `flush.py`), with recovery instructions.
5. Rewrites `origin`, fetches, fast-forwards `main`, and re-runs `uv sync`.
6. Reports before/after commit SHA so the user can see what moved.

## Step-by-step instructions

### Step 1: Preflight

Resolve the absolute path of the project root (the directory from which the user is invoking this skill — the same directory that should contain `.memory-compiler/`). Use this absolute path for every operation below.

Confirm:

- `<project-root>/.memory-compiler/` exists. If not, stop and tell the user the project has no memory-compiler install — they may want `/memory-compiler:setup` instead.
- `<project-root>/.memory-compiler/.git/` exists. If not, the directory exists but is not a git clone — stop and report; automatic migration is unsafe.

Capture the current remote URL:

```bash
git -C <project-root>/.memory-compiler remote get-url origin
```

If there is no `origin` remote, stop — manual intervention is needed.

### Step 2: Pick the target repo

Use the `AskUserQuestion` tool:

- `question`: `"Which memory-compiler repo should this install track?"`
- `header`: `"Target repo"`
- `multiSelect`: `false`
- Options:
  1. `label`: `"Cole Medin's upstream"`, `description`: `"github.com/coleam00/claude-memory-compiler — the original project"` → URL `https://github.com/coleam00/claude-memory-compiler.git`
  2. `label`: `"Wexgaard fork"`, `description`: `"github.com/wexgaard/claude-memory-compiler — fork with incremental compile, cooldown-based trigger, and prompt-context caps"` → URL `https://github.com/wexgaard/claude-memory-compiler.git`

`AskUserQuestion` automatically exposes an "Other" option for free-text input. If the user picks "Other", use the URL they type verbatim (trim whitespace; reject anything that does not look like a git URL and re-ask).

Do **not** pre-select one as recommended — migration direction is user-specific.

### Step 3: Early-exit if already on target

If the current `origin` URL already equals the chosen URL, skip the remote swap. Continue on to Step 5 (fetch + fast-forward + sync) so the install still picks up new commits.

### Step 4: Dirty-tree check

Run:

```bash
git -C <project-root>/.memory-compiler status --porcelain
```

If the output is non-empty, **stop**. The most common cause is that `/memory-compiler:show-compile-progress` has patched `flush.py` — any merge that changes that file will conflict.

Report to the user and give them the two recovery paths:

1. **Revert the progress patch, migrate, re-apply:**
   ```bash
   cp <project-root>/.memory-compiler/scripts/flush.py.preprogress.bak \
      <project-root>/.memory-compiler/scripts/flush.py
   ```
   Then re-invoke this skill, then re-invoke `/memory-compiler:show-compile-progress`.

2. **Stash, migrate, pop (may conflict):**
   ```bash
   git -C <project-root>/.memory-compiler stash push -u -m pre-migration
   ```
   Re-invoke this skill, then `git -C <project-root>/.memory-compiler stash pop`.

Do not try to auto-stash or auto-revert — the user should choose.

### Step 5: Swap remote, fetch, fast-forward, sync

If the remote needs swapping:

```bash
git -C <project-root>/.memory-compiler remote set-url origin <target-url>
```

Then, regardless of whether the remote changed:

```bash
git -C <project-root>/.memory-compiler fetch origin --prune
```

Ensure `main` is checked out (record current branch first so you can tell the user if a switch happened):

```bash
git -C <project-root>/.memory-compiler rev-parse --abbrev-ref HEAD
git -C <project-root>/.memory-compiler checkout main   # only if not already on main
```

Fast-forward:

```bash
git -C <project-root>/.memory-compiler pull --ff-only origin main
```

If `--ff-only` fails (diverged history), stop and report. Do not force, rebase, or merge without the user's explicit say-so.

Re-sync dependencies (the target repo may have a different `pyproject.toml`):

```bash
uv sync --directory <project-root>/.memory-compiler
```

### Step 6: Verify

Run three checks. If any fails, report the failure to the user and **do not** claim the migration succeeded.

**Check 1 — remote is the chosen target.**

```bash
git -C <project-root>/.memory-compiler remote get-url origin
```

Must equal the URL the user selected in Step 2.

**Check 2 — HEAD matches `origin/main`.**

```bash
git -C <project-root>/.memory-compiler rev-parse HEAD
git -C <project-root>/.memory-compiler rev-parse origin/main
```

Both SHAs must match. (They should, because Step 5 used `--ff-only`; this check catches any weird post-pull drift.)

**Check 3 — the bundled venv resolves the target's `pyproject.toml`.**

```bash
uv run --directory <project-root>/.memory-compiler python -c "import claude_agent_sdk"
```

Must exit 0. If it fails, `uv` is silently falling back to system Python and the hooks will not work — the same failure mode the `setup` skill guards against. Tell the user to re-run `uv sync --directory <project-root>/.memory-compiler` and, if that does not fix it, check the `pyproject.toml` in the migrated repo.

**Also capture, for the report:**

```bash
git -C <project-root>/.memory-compiler rev-parse --short HEAD
git -C <project-root>/.memory-compiler log -1 --pretty=%s
```

### Step 7: Report

Tell the user:

- ✅ or ❌ for each of the three checks.
- New `origin` URL and new HEAD (short SHA + subject).
- That local state (`daily/`, `knowledge/`, `scripts/state.json`, `scripts/last-flush.json`, `.venv/`) was preserved — those paths are gitignored inside the clone and are not touched by fetch/pull.
- Suggest an end-to-end sanity check: restart Claude Code in this project and confirm that the `SessionStart` hook injects the knowledge-base index. (Checks 1–3 prove migration mechanics; the hook fire is the only thing that proves the install is still wired up end-to-end.)
- If `show-compile-progress` was reverted in Step 4 option 1, remind the user to re-apply it.

## Notes

- This skill does **not** touch the project's `.claude/settings.json` — the hook commands already reference `.memory-compiler/hooks/...` by relative path, which stays valid regardless of which repo is cloned there.
