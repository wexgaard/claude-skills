---
name: setup
description: Sets up Cole Medin's Claude Memory Compiler in the current project. Use this skill when the user asks to install memory compiler, set up knowledge capture, add session memory, enable memory hooks, or wants their Claude Code sessions captured and compiled into a knowledge base. Also use when the user says 'setup memory', 'add brain', or 'install memory-compiler'.
---

# Memory Compiler Setup

This skill installs the Claude Memory Compiler into the current project and merges its hooks into the project's Claude Code configuration.

The memory compiler captures Claude Code session transcripts and compiles them into structured, cross-referenced knowledge articles following the Karpathy LLM Knowledge Base architecture.

**Note for agents executing this skill:** some harnesses persist bash cwd across tool calls and some reset it. Do not assume either. Always use absolute paths for file edits, and prefer commands like `uv sync --directory <path>` over `cd <path> && ... && cd ..`.

## What this skill does

1. Checks if `.memory-compiler/` already exists in the project root
2. If not, clones the memory compiler repo and installs dependencies
3. Reads the hook configuration from `.memory-compiler/.claude/settings.json`
4. Merges hooks into the project's `.claude/settings.json`, rewriting paths to reference `.memory-compiler/hooks/`
5. Ensures `.memory-compiler/` is listed in `.gitignore`
6. Verifies the setup is correct

## Step-by-step instructions

### Step 1: Check for existing installation

Check if `.memory-compiler/` directory exists in the project root. If it does, skip to Step 3 (hook merge) — the repo is already cloned.

### Step 2: Clone and install

**Before you begin:** Resolve the absolute path of the project root (the directory from which you are running this skill — the same directory that will contain `.memory-compiler/` after the clone). Use this absolute path for every file read and write in the remaining steps. Do not rely on the shell's current working directory, and do not use bare relative paths like `.claude/settings.json` or `.gitignore` — some harnesses persist `cd` state across tool calls, and a drifted cwd will silently retarget these edits into `.memory-compiler/` instead of the project root.

Run the following commands from the project root:

```bash
git clone https://github.com/coleam00/claude-memory-compiler.git .memory-compiler
uv sync --directory .memory-compiler
```

If `uv` is not available, inform the user they need to install it first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 3: Merge hooks

Read `<project-root>/.memory-compiler/.claude/settings.json` to get the hook definitions. (Substitute the absolute project-root path captured in Step 2 for `<project-root>` here and below.)

The memory compiler defines hooks for these events:

- `SessionStart` — injects knowledge base index into every session
- `PreCompact` — captures context before auto-compaction
- `SessionEnd` — extracts conversation into daily log

**Critical:** When merging, rewrite each hook command so that `uv` runs against the bundled project: prefix with `uv run --directory .memory-compiler` and keep the script path relative to that directory (e.g., `hooks/session-start.py`). Without `--directory`, `uv` resolves from the project root — which has no `pyproject.toml` — and silently falls back to system Python, leaving `claude_agent_sdk` unavailable to the background flush subprocess.

If the project already has a `<project-root>/.claude/settings.json`:

- Preserve all existing settings
- Merge the hooks into the existing `hooks` object
- If the same hook event already has entries, append the memory compiler hooks (do not overwrite)

If the project does not have a `<project-root>/.claude/settings.json`:

- Create `<project-root>/.claude/settings.json` with just the hook configuration

The merged configuration should look like:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory .memory-compiler python hooks/session-start.py",
            "timeout": 15
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory .memory-compiler python hooks/pre-compact.py",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory .memory-compiler python hooks/session-end.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**Sanity check before proceeding to Step 4.** Re-read `<project-root>/.claude/settings.json` and assert that:

1. `hooks.SessionStart`, `hooks.PreCompact`, and `hooks.SessionEnd` all exist as arrays.
2. At least one entry under each of the three events has a `command` field containing the substring `--directory .memory-compiler`.

If any assertion fails, stop and report the failure to the user. Do not continue to Step 4 — a half-merged `settings.json` paired with a `.gitignore` update would make the bug harder to spot.

### Step 4: Update .gitignore

Check if `<project-root>/.gitignore` exists. If it does, check if `.memory-compiler/` is already listed. If not, append it:

```
# Memory Compiler
.memory-compiler/
```

If `<project-root>/.gitignore` does not exist, create it with the above content.

### Step 5: Verify

Confirm the setup by checking:

- `.memory-compiler/` directory exists
- `.memory-compiler/.venv/` exists (uv sync succeeded)
- `.claude/settings.json` contains the three hook events
- All hook commands start with `uv run --directory .memory-compiler python hooks/...`
- `.gitignore` includes `.memory-compiler/`
- `uv run --directory .memory-compiler python -c "import claude_agent_sdk"` exits 0. If it fails, the bundled venv is not being resolved and the hooks will run under system Python.

Report the results to the user.

## Notes

- The memory compiler uses the Claude Agent SDK under the hood, which runs on your Claude subscription (Max, Team, or Enterprise). No separate API credits needed.
- Hooks fire automatically in subsequent Claude Code sessions. The current session will not have hooks active (they activate on next session start).
- Knowledge articles are compiled into `.memory-compiler/knowledge/` with an index at `.memory-compiler/knowledge/index.md`.
- Daily logs are written to `.memory-compiler/daily/`.
- Run `uv run --directory .memory-compiler python scripts/compile.py` to manually compile daily logs into knowledge articles.
- Run `uv run --directory .memory-compiler python scripts/query.py "question"` to query the knowledge base.
