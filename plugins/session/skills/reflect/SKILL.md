---
name: reflect
description: Reflects on a recently completed coding session to surface durable lessons and propose concrete updates to CLAUDE.md files, new skill ideas, or memory entries. Use when the user asks "what did we learn", "anything from this session", "session retrospective", "session reflection", "/session:reflect", "session housekeeping", or wraps a long/substantial task and wants to capture what's worth keeping. Skips trivial sessions. Proposes specific edits with file paths before applying anything.
---

# Session Reflection

End-of-session retrospective: scan what just happened, separate durable knowledge from one-off task minutiae, and propose where each piece should live.

## When to run this

- User asks variations of "what did we learn", "session retro", "anything worth saving", "session housekeeping"
- After a multi-step task wraps and there's a natural pause
- The session produced reusable patterns, bug fixes with non-obvious causes, cross-platform gotchas, or new conventions

## When NOT to run this

- Session was a single trivial change (typo, rename, one-line tweak)
- Session was pure exploration with no code changes
- Everything done is already captured by a clear commit message — there's no extra signal to extract

If the session doesn't merit it, say so plainly: "Nothing from this session needs durable capture — the commits already tell the story." Don't invent lessons to justify a deliverable.

## Procedure

### Step 1: Inventory the session

List what actually happened. Cover:

- Files created or substantially edited
- Bugs found and fixed (and the *cause*, not just the fix)
- Decisions made (what was chosen, what was rejected)
- Friction points that took multiple attempts
- Cross-platform / environmental issues encountered
- New patterns or conventions established
- Sibling repos, external systems, or services touched

Stay grounded in actual session events. Do not pad with general best practices.

### Step 2: Categorise each item

For every inventory item, pick **one** category:

| Category | Goes to | Notes |
|---|---|---|
| **Project-specific convention or pattern** | CLAUDE.md edit | Choose the closest CLAUDE.md (root only for solution-wide; sub-project file otherwise) |
| **Cross-cutting gotcha (CI, platform, env)** | CLAUDE.md edit in the most relevant sub-project | E.g. test gotchas → `tests/.../CLAUDE.md`; deployment gotchas → `src/.../CLAUDE.md` or README |
| **Reusable workflow used across projects** | New skill proposal | Only if pattern would recur in 3+ future sessions |
| **User preference, role, or working style** | Memory entry (user/feedback type) | Things the user said about *how they want to work*, not about the code |
| **Already captured by commit + code** | Nothing | Commits + grep are authoritative |

If an item doesn't clearly fit one category, default to **Nothing**. Bias toward fewer, higher-signal updates.

### Step 3: Audit existing destinations before proposing

Before proposing a CLAUDE.md edit:

- Read the target CLAUDE.md to verify the content isn't already there in different words
- Check sibling CLAUDE.md files — would this fit better elsewhere?
- Estimate the size of the addition (lines). Root CLAUDE.md should stay lean; sub-CLAUDE.md files tolerate more

Before proposing a new skill, apply the **candidacy gate** — all three must be yes:

1. **Frequency** — Does the user (or Claude on the user's behalf) do this thing 2–3+ times a week, across sessions?
2. **Same shape** — Does it follow the same pattern every time, so a fixed procedure would fit more often than it misfires?
3. **Preloaded context helps** — Would having the procedure / domain knowledge already in context measurably improve the outcome vs. re-deriving it from scratch each time?

If any answer is "no" or "not sure", don't propose a skill — propose a CLAUDE.md note or a memory entry instead, or propose nothing. Skills are expensive to maintain; the bar is high.

Then, for surviving candidates:

- Check `~/.claude/skills/` for an existing skill that overlaps — prefer updating an existing skill over adding a new one
- Ensure the trigger language is specific enough to actually fire (vague descriptions never trigger)

Before proposing a memory entry:

- Check `memory/MEMORY.md` (if present in current project's memory dir) for an existing entry on the same topic — update rather than duplicate

### Step 4: Present a proposal

Group by destination. For each item show:

- **Destination** (file path or skill name)
- **Change** (what to add, edit, or remove — show the actual lines, not paraphrase)
- **Why this is worth keeping** (one sentence)

Then ask the user via `AskUserQuestion` which items to apply. Multi-select. Default to applying nothing automatically.

### Step 5: Apply approved items

- Use `Edit` for CLAUDE.md changes
- For new skills, invoke the `skill-creator` skill (via the `Skill` tool) with the candidate's name, trigger phrases, and procedure outline — let it produce the SKILL.md. Don't raw-`Write` a SKILL.md yourself; skill-creator's scaffolding (frontmatter discipline, degrees-of-freedom guidance, anti-patterns) is the whole reason it exists.
- Use the memory-write convention for memory entries (separate `.md` file + `MEMORY.md` pointer)
- Commit CLAUDE.md changes with a `docs:` prefix conventional commit. Don't commit memory entries or skill files (both live outside the repo).

## Anti-patterns

- **Don't restate commit messages.** If the lesson is "we added a Dockerfile", that's the commit — not a CLAUDE.md entry.
- **Don't bloat root CLAUDE.md.** Lean root, fat leaves. Solution-wide things only at root.
- **Don't propose skills for things that happen once.** Skills are for *recurring* patterns. A one-off bug fix is not a skill.
- **Don't invent.** If the session was unremarkable, say so. The user trusts honest "nothing here" more than fabricated reflection.
- **Don't paraphrase the change.** Show the exact text you'd add or remove so the user can decide on substance, not on your summary.

## Example proposal shape

```
## CLAUDE.md updates (3)

**tests/.../CLAUDE.md** — add `## Cross-platform gotchas` section
  +12 lines covering Uri.TryCreate Linux/Windows divergence, line endings, paths
  Why: this bit us in CI today; will recur as more tests get added

**root CLAUDE.md** — add `## Sibling repos` section
  +5 lines pointing to o8g.web and o8g.infra
  Why: future Claude opening the repo cold has no way to know these exist

**src/o8g.Api/CLAUDE.md** — replace `## Configuration` paragraph with a layered table
  -1 line, +12 lines
  Why: production added appsettings.Production.json today; current doc only mentions Local.json

## Skill proposals (0)
Nothing from this session is a recurring cross-project pattern.

## Memory entries (0)
No new user preferences or working-style signals surfaced.
```
