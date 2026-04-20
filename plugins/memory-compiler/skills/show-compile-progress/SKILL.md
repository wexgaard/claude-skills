---
name: show-compile-progress
description: Replaces the empty "claude" popup that memory-compiler shows during end-of-day compile with a banner, spinner, and live step log. Use this skill when the user asks to show memory compile progress, make the compile window informative, fix the empty claude popup, add a progress indicator to memory compiler, or says something like "why is that black window empty" or "show what compile is doing". Requires memory-compiler to already be installed via /memory-compiler:setup.
---

# Show Compile Progress

This skill makes `memory-compiler`'s end-of-day compile step visible: instead of the empty console window titled "claude" that pops up after 6 PM, the compile runs inside a launcher that prints a banner, animates a spinner, and streams every step as it happens. The window closes by itself when the compile finishes.

It is strictly opt-in — users who are fine with the silent popup do not need this skill.

**Note for agents executing this skill:** bash cwd behavior differs across harnesses. Always use absolute paths and prefer `uv run --directory <path>` over `cd <path>`. The paths in this skill are given relative to the project root (the same directory that contains `.memory-compiler/`); resolve the absolute project-root path up front and use it for every file read and write.

## What this skill does

1. Verifies that `.memory-compiler/` is installed in the project root.
2. Writes a launcher script at `.memory-compiler/scripts/compile-launcher.py`.
3. Patches `.memory-compiler/scripts/flush.py` so its end-of-day compile spawn runs the launcher instead of `compile.py` directly, in a visible console window.
4. Saves a backup of the original `flush.py` so the change can be reverted.

## Step-by-step instructions

### Step 1: Preflight

Resolve the absolute path of the project root (the directory containing `.memory-compiler/`). Use this absolute path for every file operation below.

Confirm the following exist:

- `<project-root>/.memory-compiler/` — if missing, stop and tell the user to run `/memory-compiler:setup` first.
- `<project-root>/.memory-compiler/scripts/flush.py`
- `<project-root>/.memory-compiler/scripts/compile.py`

If any upstream script is missing, the memory-compiler install is incomplete; do not proceed.

### Step 2: Idempotency check

Check whether this skill has already been applied:

- If `<project-root>/.memory-compiler/scripts/compile-launcher.py` exists **and** `<project-root>/.memory-compiler/scripts/flush.py` contains the substring `compile-launcher.py`, the skill is already installed. Report this to the user and stop.
- If one exists but not the other, the previous install is half-applied. Stop and ask the user whether to re-apply (which will overwrite the launcher and re-patch `flush.py`) or to investigate first.

### Step 3: Write the launcher

Copy `templates/compile-launcher.py` (from this skill directory) to `<project-root>/.memory-compiler/scripts/compile-launcher.py`. Write it with UTF-8 encoding and LF or CRLF consistent with the existing scripts in that directory.

### Step 4: Patch flush.py

Back up the original:

```
<project-root>/.memory-compiler/scripts/flush.py
  -> <project-root>/.memory-compiler/scripts/flush.py.preprogress.bak
```

Apply exactly three substitutions inside `flush.py`. Each anchor is unique — match it exactly, do **not** use regex replacements that could over-match.

**Substitution 1** — change the spawned script.

Anchor (exact):

```
compile_script = SCRIPTS_DIR / "compile.py"
```

Replace with:

```
compile_script = SCRIPTS_DIR / "compile-launcher.py"
```

**Substitution 2** — change the Windows creation flags so the spawned process gets a real visible console (instead of `DETACHED_PROCESS`, which allocates an empty one).

Anchor (exact):

```
        kwargs["creationflags"] = _sp.CREATE_NEW_PROCESS_GROUP | _sp.DETACHED_PROCESS
```

Replace with:

```
        kwargs["creationflags"] = _sp.CREATE_NEW_CONSOLE | _sp.CREATE_NEW_PROCESS_GROUP
```

**Substitution 3** — stop redirecting the launcher's stdout/stderr to `compile.log`. The launcher writes directly to the console and tees child output to `compile.log` itself; leaving the redirect in place would silence the launcher's UI.

Anchor (exact, three lines inside the `try:` block):

```
        log_handle = open(str(SCRIPTS_DIR / "compile.log"), "a")
        _sp.Popen(cmd, stdout=log_handle, stderr=_sp.STDOUT, cwd=str(ROOT), **kwargs)
```

Replace with:

```
        _sp.Popen(cmd, cwd=str(ROOT), **kwargs)
```

### Step 5: Verify

Re-read `<project-root>/.memory-compiler/scripts/flush.py` and confirm all three substitutions landed:

1. `compile_script = SCRIPTS_DIR / "compile-launcher.py"` appears once.
2. `CREATE_NEW_CONSOLE | CREATE_NEW_PROCESS_GROUP` appears once.
3. The old `log_handle = open(...)` line is gone and the Popen call no longer has `stdout=` / `stderr=` arguments.

Confirm `<project-root>/.memory-compiler/scripts/compile-launcher.py` exists and is non-empty.

### Step 6: Summarize for the user

Tell the user:

- The change was applied: after 6 PM local time, end-of-day compiles will now show a labelled window with a spinner and live step log instead of an empty "claude" popup.
- The window will close by itself when the compile finishes.
- The original `flush.py` is backed up at `.memory-compiler/scripts/flush.py.preprogress.bak` — to revert, copy it back over `flush.py` and delete `compile-launcher.py`.
- If they later re-clone `.memory-compiler/` (for example, to pick up upstream changes), they will need to re-run `/memory-compiler:show-compile-progress` to re-apply the patch.

## Notes

- The patch modifies upstream code cloned from `github.com/coleam00/claude-memory-compiler`. The patch is intentionally small (three anchored substitutions) to minimize the chance of conflict with upstream updates.
- No change is made to `.claude/settings.json` — the existing `SessionEnd` hook is untouched. The progress UI is entirely internal to how `flush.py` spawns its end-of-day compile.
- The launcher tees child output to `compile.log` as before, so existing log-based debugging still works.
