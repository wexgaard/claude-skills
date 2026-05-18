---
name: commit-push
description: Stage, commit, and push changes with a generated conventional commit message. Use when the user wants to commit and push in one step (e.g. "commit and push", "/git:commit-push", "stage, commit and push").
disable-model-invocation: true
---

1. Run the `commit` skill end-to-end — same staging, message generation, and rules apply.
2. If the commit succeeded, push to the current remote branch: `git push`.

## Additional rules
- Never force-push to `main`/`master` — warn the user if asked.
- If `commit` stopped (nothing to commit, sensitive files flagged), stop too — don't push a stale HEAD.
