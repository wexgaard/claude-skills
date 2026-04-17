---
name: memory-compiler-setup
description: Sets up Cole Medin's Claude Memory Compiler in the current project. Use this skill when the user asks to install memory compiler, set up knowledge capture, add session memory, enable memory hooks, or wants their Claude Code sessions captured and compiled into a knowledge base. Also use when the user says 'setup memory', 'add brain', or 'install memory-compiler'.
---

# Memory Compiler Setup

This skill installs the Claude Memory Compiler into the current project and merges its hooks into the project's Claude Code configuration.

The memory compiler captures Claude Code session transcripts and compiles them into structured, cross-referenced knowledge articles following the Karpathy LLM Knowledge Base architecture.

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

Run the following commands from the project root:

```bash
git clone https://github.com/coleam00/claude-memory-compiler.git .memory-compiler
cd .memory-compiler && uv sync && cd ..
```

If `uv` is not available, inform the user they need to install it first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 3: Merge hooks

Read `.memory-compiler/.claude/settings.json` to get the hook definitions.

The memory compiler defines hooks for these events:

- `SessionStart` — injects knowledge base index into every session
- `PreCompact` — captures context before auto-compaction
- `SessionEnd` — extracts conversation into daily log

**Critical:** When merging, rewrite all hook command paths from relative (e.g., `uv run python hooks/session-start.py`) to reference the `.memory-compiler/` subdirectory (e.g., `uv run python .memory-compiler/hooks/session-start.py`).

If the project already has a `.claude/settings.json`:

- Preserve all existing settings
- Merge the hooks into the existing `hooks` object
- If the same hook event already has entries, append the memory compiler hooks (do not overwrite)

If the project does not have a `.claude/settings.json`:

- Create `.claude/settings.json` with just the hook configuration

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
            "command": "uv run python .memory-compiler/hooks/session-start.py",
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
            "command": "uv run python .memory-compiler/hooks/pre-compact.py",
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
            "command": "uv run python .memory-compiler/hooks/session-end.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### Step 4: Update .gitignore

Check if `.gitignore` exists in the project root. If it does, check if `.memory-compiler/` is already listed. If not, append it:

```
# Memory Compiler
.memory-compiler/
```

If `.gitignore` does not exist, create it with the above content.

### Step 5: Verify

Confirm the setup by checking:

- `.memory-compiler/` directory exists
- `.memory-compiler/.venv/` exists (uv sync succeeded)
- `.claude/settings.json` contains the three hook events
- All hook command paths reference `.memory-compiler/hooks/`
- `.gitignore` includes `.memory-compiler/`

Report the results to the user.

## Notes

- The memory compiler uses the Claude Agent SDK under the hood, which runs on your Claude subscription (Max, Team, or Enterprise). No separate API credits needed.
- Hooks fire automatically in subsequent Claude Code sessions. The current session will not have hooks active (they activate on next session start).
- Knowledge articles are compiled into `.memory-compiler/knowledge/` with an index at `.memory-compiler/knowledge/index.md`.
- Daily logs are written to `.memory-compiler/daily/`.
- Run `uv run python .memory-compiler/scripts/compile.py` to manually compile daily logs into knowledge articles.
- Run `uv run python .memory-compiler/scripts/query.py "question"` to query the knowledge base.
