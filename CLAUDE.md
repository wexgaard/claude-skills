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

Skills live under `plugins/<plugin-name>/skills/<skill-name>/SKILL.md`. The
filename is always literally `SKILL.md`; the *skill name* comes from the
`name:` field in the frontmatter and the containing directory name (they
must match).

## Naming: plugins are namespaces, skills are actions

Claude Code exposes plugin skills as `/<plugin-name>:<skill-name>`. Name
them so that combination reads naturally:

- Plugin name = the subject / topic (e.g. `memory-compiler`, `deploy`,
  `db`)
- Skill name = the verb / action (e.g. `setup`, `rollback`, `seed`)

This gives slash commands like `/memory-compiler:setup`, `/deploy:rollback`,
`/db:seed`. **Avoid redundant pairs** like
`/memory-compiler-setup:memory-compiler-setup` — if the plugin and skill
have the same name, one of them is over-specified.

A plugin can host multiple related skills, so prefer plugin names broad
enough to grow (e.g. `memory-compiler` can later host `update`,
`uninstall`, `query` alongside `setup`).

## Adding a new skill

When adding a new skill/plugin to this repo:

1. Pick names per the convention above (plugin = subject, skill = action).
2. Create `plugins/<plugin>/.claude-plugin/plugin.json` (name, version,
   description, author).
3. Create `plugins/<plugin>/skills/<skill>/SKILL.md` with frontmatter
   (`name: <skill>`, `description: ...`) and the skill body. The
   `description` must list the trigger phrases that should invoke the skill,
   since that is what Claude uses to decide whether to run it.
4. Register the plugin in `.claude-plugin/marketplace.json` under `plugins`
   (name, `source: ./plugins/<plugin>`, description, category).
5. **Update `README.md`** — add a row to the "Available Skills" table and,
   if the install commands differ from existing ones, extend the
   installation examples. The README is the only human-facing index of what
   this marketplace offers, so it must stay in sync with
   `marketplace.json`.

## Adding a skill to an existing plugin

If the new skill belongs to an existing plugin's namespace, skip steps 2
and 4 — just add a new `plugins/<plugin>/skills/<skill>/SKILL.md` and add a
row to the README table.

## Conventions

- Marketplace name: `wexgaard-skills`
- Owner / author: `Wexgaard`
- Default plugin category: `development` (override when a different category
  fits better)
- Plugin `source` in `marketplace.json` is a repo-relative path
  (`./plugins/<plugin>`)
- Plugin version starts at `0.1.0` and follows semver
