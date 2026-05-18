---
name: audit
description: Audits installed Claude skills under ~/.claude/skills/ for visibility risk (side-effecting skills that should be auto-fire-disabled, background-knowledge skills that should be hidden from /menu), non-deterministic steps that should be scripts, and duplicated logic across skills. Use when the user asks to "audit skills", "audit my skills", "review skills", "/skill:audit", "skill hygiene", "skill housekeeping", or "clean up skills". Reports findings as a per-skill punch list and applies edits only after explicit approval.
---

# Skill Audit

Maintenance pass over `~/.claude/skills/`: surface skills whose visibility settings don't match their risk profile, steps that ask the model to do work a script would do better, and logic duplicated across skills. Audit-only — does not add new skills (that's `skill-creator`'s job) or reflect on the session (that's `/session:reflect`'s job).

## When to run this

- User explicitly asks: "audit skills", "review my skills", "skill hygiene"
- After installing several new skills in a short period
- Periodically on long-lived skill collections (months between audits)

## When NOT to run this

- Right after `skill-creator` produced a new skill — it was just curated
- Skill collection has fewer than ~3 user-authored skills (nothing to dedupe yet)

## Procedure

### Step 1: Inventory

`Glob` `~/.claude/skills/**/SKILL.md` (on Windows the same path resolves under `%USERPROFILE%\.claude\skills\`). For each, read the frontmatter and note:

- Skill name
- Description (first sentence)
- Total line count
- Presence of `scripts/`, `references/`, `assets/` subfolders
- Current `disable-model-invocation` and `user-invocable` values (if set)

Report the inventory before proceeding so the user sees scope.

### Step 2: Audit each skill across three dimensions

#### a) Visibility — does the trigger surface match the risk?

For every skill, classify it on two axes and check whether the frontmatter matches:

**Side-effect risk (auto-fire safety):**
- *High-side-effect* skills perform irreversible or externally visible actions: deploy, commit-push, send messages (email, Slack), publish, force-push, drop tables, schedule remote agents.
- *Low-side-effect* skills only read, plan, propose edits the user must approve, or do local-only reversible work.

→ High-side-effect skills should have `disable-model-invocation: true` in frontmatter so Claude cannot auto-fire them from a description match. The user must invoke explicitly.

**Discoverability (menu surface):**
- *User-actionable* skills the user might run themselves via `/menu` or `/<name>`: commit, deploy, init, review.
- *Background-knowledge* skills that exist purely to inform Claude when it's already doing something: domain references, style guides, "how to write Foo" packs. The user would never type `/<name>` themselves.

→ Background-knowledge skills should have `user-invocable: false` so they're hidden from `/menu` (still loaded when their description matches what Claude is doing).

Record any mismatch: skill name, the field that's wrong, and the one-line reason.

#### b) Deterministic vs non-deterministic — find AI doing scriptable work

Read each skill's body. For every step, ask: **could a script do this with the same or better result?**

Common scriptable patterns hidden inside AI steps:
- "List all files matching X" — `Glob` is already deterministic, but a wrapping shell script is even cheaper if the same listing is reused
- "Parse this YAML / JSON / TOML and extract field Y" — script
- "Compute file line counts, sort by size" — script
- "Validate that every link in MEMORY.md points to a file that exists" — script
- "Walk the CLAUDE.md tree and produce an index" — script
- Any "for each X in Y, do the same Z" where Z is mechanical — script

Keep AI for steps that require judgment:
- "Decide whether this content belongs in root or sub CLAUDE.md"
- "Draft a commit message that captures the why"
- "Group findings by severity"

Each scriptable step found = one finding. Note the skill, the step, and what the script would do. Code = same result every time, no token cost.

#### c) Composability — flag duplicated logic across skills

Look for the same logic appearing in multiple skills. Common duplicates:
- Reading and parsing `MEMORY.md`
- Walking the CLAUDE.md tree
- Drafting conventional commit messages
- Producing an `AskUserQuestion` multi-select for "which of these N findings to apply"
- Staging + committing with a specific prefix

For each duplicate cluster, propose either:
- A small shared script in a common location (e.g. `~/.claude/skills/_shared/scripts/`) both skills call, OR
- A smaller composable skill the others delegate to

Don't flag conceptual overlap that's intentional (e.g. `/claude-md:audit` and `/skill:audit` both having an "inventory → findings → propose → apply" shape is fine — that's the audit pattern, not duplication).

### Step 3: Report

Per-skill punch list, scannable:

```
## commit-push (45 lines)

- ✗ High-side-effect (pushes to remote) but `disable-model-invocation` not set — Claude could auto-fire on a vague description match
- ⚠ Step "scan transcript for last N commits" could be a small script in scripts/recent-commits.sh

## boris (380 lines)

- ✗ Pure background knowledge — `user-invocable: false` recommended (no one types `/boris` to invoke it)
- ✓ No scriptable AI steps, no duplication

## claude-md:audit & skill:audit (this file)

- ⚠ Both produce "AskUserQuestion multi-select grouped by file" — consider a shared helper script
```

Use `✓` clean / `⚠` minor / `✗` actionable.

### Step 4: Propose edits

For each `⚠` or `✗`, draft the specific change:

- **Visibility fixes**: show the exact frontmatter lines to add
- **Script extractions**: name the script path, sketch its inputs/outputs, and show which prose lines in the skill it replaces
- **Composability**: show the shared-script path and which skills would call it

Ask the user via `AskUserQuestion` which to apply (multi-select, default nothing).

### Step 5: Apply approved edits

- `Edit` for frontmatter additions
- `Write` for new scripts under `scripts/` (inside the skill) or `~/.claude/skills/_shared/scripts/` (cross-skill)
- After writing a script, `Edit` the skill body to call it instead of describing the work in prose
- Skill changes live outside the project repo — no commit. If the user keeps `~/.claude/` in a dotfiles repo, mention it but don't auto-commit there either.

## Anti-patterns

- **Don't add new skills.** This audit removes, hides, and extracts only. New skills are `skill-creator`'s job.
- **Don't flag style.** "I'd phrase this section differently" is not a finding. Substance only: wrong visibility, scriptable step, duplicate logic.
- **Don't trust descriptions over bodies.** A skill's actual risk lives in what its body tells Claude to do, not in the marketing in the description.
- **Don't extract a script for one-time work.** Scripts pay off when called repeatedly. A single mechanical step inside one skill is not worth the indirection.
- **Don't auto-apply.** Every change goes through `AskUserQuestion`. Wrongly disabling auto-invocation on a skill the user relies on is annoying to discover later.

## Output shape recap

Inventory → per-skill findings (✓/⚠/✗) across visibility, determinism, composability → drafted edits → user picks → apply.
