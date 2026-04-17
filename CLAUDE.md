# Wexgaard Claude Skills

This repo is a **Claude Code plugin marketplace** (`wexgaard-skills`) that
distributes skills as installable plugins.

## Layout

```
.claude-plugin/marketplace.json           # marketplace manifest (lists all plugins)
plugins/<plugin-name>/
  .claude-plugin/plugin.json              # per-plugin manifest
  skills/<skill-name>/SKILL.md            # the skill definition
README.md                                 # human-facing index of available skills
```

Each plugin in `plugins/` must be registered in the `plugins` array of
`.claude-plugin/marketplace.json`, and must contain its own
`.claude-plugin/plugin.json`.

Skills live under `plugins/<plugin-name>/skills/<skill-name>/SKILL.md` — one
skill per directory, named identically to the directory.

## Adding a new skill

When adding a new skill/plugin to this repo:

1. Create `plugins/<name>/.claude-plugin/plugin.json` (name, version,
   description, author).
2. Create `plugins/<name>/skills/<name>/SKILL.md` with the skill frontmatter
   and body.
3. Register the plugin in `.claude-plugin/marketplace.json` under `plugins`
   (name, source path, description, category).
4. **Update `README.md`** — add a row to the "Available Skills" table and, if
   relevant, extend the installation examples. The README is the only
   human-facing index of what this marketplace offers, so it must stay in
   sync with `marketplace.json`.

## Conventions

- Marketplace name: `wexgaard-skills`
- Owner / author: `Wexgaard`
- Default plugin category: `development` (override when a different category
  fits better)
- Plugin `source` in `marketplace.json` is a repo-relative path
  (`./plugins/<name>`)
