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
| `memory-compiler` | `setup` | Installer for Cole Medin's Claude Memory Compiler. Clones the upstream repo into any project, merges its hooks into the project's Claude Code settings, and updates `.gitignore` to enable automatic session capture and knowledge compilation. |
| `memory-bridge` | `sync` | Forwards `memory-compiler` daily logs to a configurable HTTP ingestion endpoint on each `SessionEnd`, so per-project session knowledge can feed a cross-project memory store. The forwarder is stdlib-only and POSTs JSON with an `X-API-Key` header; the exact payload and endpoint shape are documented in the skill. Also handles rotate-key / reconfigure / status / force-today on re-run. |

## Requirements

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) (Pro, Max, Team, or Enterprise)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Git

## Credits

- [Cole Medin](https://github.com/coleam00) — [Claude Memory Compiler](https://github.com/coleam00/claude-memory-compiler)