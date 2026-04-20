# Wexgaard Claude Skills

A collection of Claude Code skills for AI-assisted development workflows.

## Installation

### Via Claude Code plugin marketplace

```
/plugin marketplace add wexgaard/claude-skills
/plugin install memory-compiler@wexgaard-skills
```

Invoke the installed skill in any project with `/memory-compiler:setup`.

### Manual

Bash (macOS / Linux / WSL / Git Bash):

```bash
git clone https://github.com/wexgaard/claude-skills.git
cp -r claude-skills/plugins/memory-compiler/skills/setup ~/.claude/skills/memory-compiler-setup
```

PowerShell (Windows):

```powershell
git clone https://github.com/wexgaard/claude-skills.git
Copy-Item -Recurse -Path "claude-skills\plugins\memory-compiler\skills\setup" -Destination "$env:USERPROFILE\.claude\skills\memory-compiler-setup"
```

## Available Skills

| Plugin | Skill | Description |
|--------|-------|-------------|
| `memory-compiler` | `setup` | Installer for Cole Medin's Claude Memory Compiler. Clones the upstream repo into any project, merges its hooks into the project's Claude Code settings, and updates `.gitignore` to enable automatic session capture and knowledge compilation. |
| `memory-bridge` | `sync` | Forwards `memory-compiler` daily logs to a configurable HTTP ingestion endpoint on each `SessionEnd`, so per-project session knowledge can feed a cross-project memory store. The forwarder is stdlib-only and POSTs JSON with an `X-API-Key` header; the exact payload and endpoint shape are documented in the skill. Also handles rotate-key / reconfigure / status / force-today on re-run. |

## Requirements

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) (Pro, Max, Team, or Enterprise)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Git

## Credits

- [Cole Medin](https://github.com/coleam00) — [Claude Memory Compiler](https://github.com/coleam00/claude-memory-compiler)