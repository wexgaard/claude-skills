---
name: audit
description: Audits all CLAUDE.md files in the current project for staleness, redundancy, and bloat — dead file or symbol references, duplicate content across sibling files, oversized sections, outdated patterns. Use when the user asks to "audit CLAUDE.md", "/claude-md:audit", "check the docs", "are the docs stale", "clean up project docs", or before a major refactor. Reports findings as a punch list grouped by file and applies edits only after explicit approval.
---

# CLAUDE.md Audit

Maintenance pass over the CLAUDE.md tree: find references that no longer match the code, redundancy that should be deduped, and bloat that should be trimmed. Does not add new content — that's the job of `/session:reflect`.

## When to run this

- User explicitly asks: "audit claude.md", "are the docs stale", "clean up project docs"
- Before a major refactor — the existing CLAUDE.md may be guiding Claude toward patterns that are about to change
- Periodically on long-lived projects (months between audits)

## When NOT to run this

- Right after `/session:reflect` ran — the new content was just curated
- On a brand-new project with one or two CLAUDE.md files of trivial size

## Procedure

### Step 1: Inventory

`Glob` for `**/CLAUDE.md` in the current working directory. List the files with their line counts (use `Bash` with `wc -l` or read each and count).

Report the inventory before proceeding so the user sees the scope.

### Step 2: Audit each file

For every CLAUDE.md, check these categories in order:

#### a) Dead references

Every concrete reference is a claim that something exists. Verify:

- **File paths** mentioned in prose or tables: `Glob` or `Read` to confirm the file exists at that path
- **Function / class / type names**: `Grep` for the symbol; if zero hits in production code, it's dead
- **Folder structures** (e.g. ASCII tree diagrams): cross-check against current layout via `Glob`
- **Commands** (e.g. `dotnet ef ...`, `npm run ...`): verify the script/target still exists in the relevant config file
- **External URLs**: don't bother checking unless they're load-bearing (do not WebFetch every URL just to validate it)

For each dead reference: record file + line + the broken claim.

#### b) Redundancy across sibling files

For each sub-project CLAUDE.md, check whether content is duplicated in the root CLAUDE.md or in another sibling. The pattern is usually:

- Root CLAUDE.md should describe **solution-wide** conventions
- Each sub-CLAUDE.md should describe **what's unique to that sub-project**
- If both say the same thing, the sub-project version is usually the one to keep (more specific context); the root version is the one to thin

Look for verbatim or near-verbatim paragraphs across files. Don't flag conceptual overlap that's intentional (e.g. both files mentioning "Result pattern" with different angles is fine).

#### c) Oversized sections

Skim each section. Flag any single section over ~50 lines as a candidate for either splitting (move details into a reference markdown alongside) or trimming. The 500-line whole-file limit from skill best practices applies here too — if a CLAUDE.md is over 500 lines, propose a split.

#### d) Outdated patterns

Look for content that describes the codebase as it was, not as it is:

- "We use X for Y" — does the code still use X?
- Migration notes that are months old and clearly completed
- "Coming soon: Z" — is Z still coming?
- Version pins (".NET 9") that have drifted from reality

This requires reading actual code, not just the doc. Spot-check rather than exhaustively verify.

### Step 3: Report

Produce a per-file punch list. Keep it scannable:

```
## root CLAUDE.md (64 lines)

- ✓ All references resolve
- ⚠ Duplicates `src/o8g.Api/CLAUDE.md` Configuration paragraph — trim root version
- ⚠ Section `## Dependencies` is 14 lines but largely restates project policy that's also in the per-project files

## src/o8g.Application/CLAUDE.md (104 lines)

- ✗ Dead reference: line 47 mentions `IWidgetService` but the project never had a Widget aggregate — looks like a leftover template example
- ✓ No redundancy, no oversized sections
```

Use `✓`, `⚠`, `✗` for clean / minor / actionable findings.

### Step 4: Propose edits

For each `⚠` or `✗` finding, draft the specific edit: which lines to remove, replace, or move. Don't show "I'd refactor this section" — show the diff.

Ask the user via `AskUserQuestion` which to apply. Group as multi-select.

### Step 5: Apply approved edits

- Use `Edit` for targeted changes
- For splits (moving content into a new file), `Write` the new file then `Edit` the original to reference it
- Commit with a `docs:` or `chore(docs):` conventional commit covering all approved changes in one go

## Anti-patterns

- **Don't add new content.** This skill removes and reorganises only. New content is `/session:reflect`'s job.
- **Don't flag style.** "I'd phrase this differently" is not a finding. Substance only: dead, duplicate, oversized, outdated.
- **Don't trust the doc over the code.** When CLAUDE.md and the code disagree, the code wins — flag the doc as outdated.
- **Don't audit external URLs by fetching them all.** Slow, wasteful, low signal.
- **Don't auto-apply.** Every change goes through `AskUserQuestion` first. A wrongly-removed paragraph is harder to recover than one extra prompt.

## Output shape recap

Inventory → per-file findings (✓/⚠/✗) → drafted edits → user picks → apply → commit.
