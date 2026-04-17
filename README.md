# Wexgaard Claude Skills

A plugin marketplace for Claude Code with skills for AI-assisted development workflows.

## Installation

Register the marketplace (one-time):

```
/plugin marketplace add wexgaard/claude-skills
```

Then install individual skills:

```
/plugin install memory-compiler-setup@wexgaard-skills
```

## Available Skills

| Skill | Description |
|-------|-------------|
| `memory-compiler-setup` | Installs Cole Medin's Claude Memory Compiler into any project. Clones the repo, merges hooks into the project's Claude Code settings, and configures `.gitignore`. Enables automatic session capture and knowledge compilation. |

## Requirements

- Claude Code (Pro, Max, Team, or Enterprise)
- `uv` (Python package manager)
- `git`