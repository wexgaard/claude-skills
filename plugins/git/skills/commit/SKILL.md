---
name: commit
description: Stage and commit changes with a generated conventional commit message. Use when the user wants to commit only (e.g. "commit", "/git:commit"). For commit + push, use commit-push instead.
---

1. Run `git status` and `git diff HEAD` in parallel to see what changed
2. If nothing is staged, run `git add -A`
3. Generate a conventional commit message from the diff:
   - Format: `<type>(<scope>): <description>` — imperative, lowercase, no period, max 72 chars
   - Types: `feat` | `fix` | `refactor` | `chore` | `docs` | `style` | `test` | `perf`
   - Scope: feature area (e.g. `sessions`, `auth`, `i18n`) — omit if changes are broad
   - Add a body only if non-obvious context is needed
4. Commit using a heredoc to preserve formatting

## Rules
- Never amend published commits or use `--no-verify`
- If untracked files look sensitive (`.env`, credentials), ask before staging
- If nothing to commit, say so and stop
