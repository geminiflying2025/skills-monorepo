# Skills Monorepo Maintenance

## Source of Truth

This repository is the source of truth for custom maintained skills.

- Develop here
- Review here
- Version here with git
- Deploy from here to runtime targets

Do not treat `~/.openclaw/skills` as the primary authoring location.
It is a runtime/install target only.

## Layout

- `skills/<skill-name>/` — one self-contained skill package
- `scripts/deploy-skill.sh` — deploy one skill to local or remote target
- `scripts/deploy-all.sh` — deploy all managed skills

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

## Rules

1. Keep every skill self-contained
2. No absolute machine-specific paths
3. Use ASCII directory names for packaged assets when possible
4. Do not commit `node_modules`, `.venv`, cache directories, or build output
5. Put reusable templates/assets inside the skill package itself

## Suggested next migrations

Bring only genuinely maintained custom skills into this repo, for example:
- market-report
- notebooklm-docs
- readurl
- single-product-report
- wisdom-news-brief
