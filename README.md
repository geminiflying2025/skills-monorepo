# skills-monorepo

Source repository for developing and maintaining custom skills.

This repository is the authoring workspace for skills development. It is not
the live runtime location where skills are loaded from. Treat it as the source
of truth for skill structure, prompts, scripts, references, and packaged
assets.

## What This Repo Is For

- Develop custom skills in a versioned workspace
- Review and iterate on `SKILL.md`, helper scripts, and packaged assets
- Keep reusable references and templates inside each skill package
- Deploy completed skills to a separate runtime/install target

## What This Repo Is Not

- Not the primary runtime directory
- Not the place where the host app directly loads installed skills from
- Not a scratch folder for machine-local edits that bypass version control

## Lifecycle

1. Author or update a skill in this repository
2. Review the skill here
3. Commit the change here
4. Deploy the skill to a runtime target with the scripts in `scripts/`

## Structure

- `skills/` — one directory per skill package
- `scripts/` — deployment helpers for local or remote targets
- `inventory/` — registry of managed and third-party skills
- `docs/` — design notes and longer-lived project documentation

## Core Principles

- Develop skills here, not directly inside `~/.openclaw/skills`
- Treat `~/.openclaw/skills` as an install/runtime target only
- Keep each skill self-contained
- Prefer relative, package-local paths over machine-specific absolute paths
- Put reusable scripts, assets, and references inside the skill package

## Quick Start

Deploy one skill locally:

```bash
./scripts/deploy-skill.sh market-report local
```

Deploy all managed skills locally:

```bash
./scripts/deploy-all.sh local
```

For detailed maintenance and authoring conventions, see
`docs-MAINTENANCE.md`.
