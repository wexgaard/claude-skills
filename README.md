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
| `memory-compiler` | `setup` | Installs the Claude Memory Compiler into any project. Clones the repo, merges hooks into the project's Claude Code settings, and configures `.gitignore`. Enables automatic session capture and knowledge compilation. |

## Requirements

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) (Pro, Max, Team, or Enterprise)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Git

## Credits

- [Cole Medin](https://github.com/coleam00) — [Claude Memory Compiler](https://github.com/coleam00/claude-memory-compiler)