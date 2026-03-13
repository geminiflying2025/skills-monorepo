# Skills Monorepo Maintenance

## Repository Role

This repository is the source of truth for custom maintained skills.

- Develop here
- Review here
- Version here with git
- Deploy from here to runtime targets

Do not treat `~/.openclaw/skills` as the primary authoring location. It is a
runtime/install target only.

## Repository Layout

- `skills/<skill-name>/` — one self-contained skill package
- `scripts/deploy-skill.sh` — deploy one skill to a local or remote runtime
- `scripts/deploy-all.sh` — deploy all managed skills
- `inventory/custom-skills.yaml` — managed custom skills registry
- `inventory/third-party-skills.yaml` — installed third-party skills registry

## Skill Package Expectations

Each skill should be packaged so it can be developed, reviewed, and deployed as
one unit.

Recommended contents:

- `SKILL.md` — the skill contract and operating instructions
- `scripts/` — helper scripts used by the skill
- `references/` — prompts, schemas, examples, or supporting notes
- `assets/` — templates or bundled static resources

Keep dependencies and implementation details inside the skill directory whenever
practical.

## Authoring Rules

1. Keep every skill self-contained.
2. Prefer package-local relative paths over machine-specific absolute paths.
3. Use placeholders like `<skill-dir>` inside `SKILL.md` when describing file
   locations or commands.
4. Do not hardcode runtime-only paths in skill documentation unless the runtime
   target itself is the subject being documented.
5. Use ASCII directory names for packaged assets when possible.
6. Do not commit `node_modules`, `.venv`, cache directories, generated build
   output, or other disposable artifacts.
7. Put reusable templates, prompts, and assets inside the skill package rather
   than in ad hoc external locations.

## Source vs Runtime Boundary

Keep these roles separate:

- This repository: authoring, review, version control, packaging
- Runtime target such as `~/.openclaw/skills`: installation and execution

That boundary should be reflected in the docs:

- `README.md` and maintenance docs should describe this repository as the
  development home
- `SKILL.md` files should prefer `<skill-dir>`-style references for packaged
  scripts and assets
- Deployment scripts may reference runtime targets directly because that is
  their job
- Inventory files may record machine paths as operational metadata, but those
  paths should not become the default authoring convention

## Output Convention

When running skills from this repository for development or verification,
default generated artifacts should be written to the repository root `output/`
directory.

- Put temporary or reviewable outputs in `./output/`
- Do not commit generated output files
- Keep only a placeholder file such as `output/.gitkeep` so the directory
  exists in a clean checkout

## Deployment

### Deploy one skill locally

```bash
./scripts/deploy-skill.sh market-report local
```

### Deploy one skill to another machine

```bash
./scripts/deploy-skill.sh market-report newmini
```

### Deploy all managed skills

```bash
./scripts/deploy-all.sh local
./scripts/deploy-all.sh newmini
```

## Review Checklist

Before deploying a changed skill, check:

1. `SKILL.md` matches the current implementation and packaged files
2. Commands in the docs resolve from the packaged skill directory
3. No secrets, tokens, local databases, or machine-private files are included
4. Bundled assets and helper scripts are actually needed by the skill
5. The skill can still be copied cleanly by the deploy scripts

## Suggested Next Migrations

Bring only genuinely maintained custom skills into this repo, for example:

- `market-report`
- `notebooklm-docs`
- `readurl`
- `single-product-report`
- `wisdom-news-brief`
