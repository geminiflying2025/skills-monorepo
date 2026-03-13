# skills-monorepo

Custom skills monorepo for OpenClaw-related workflows.

## Structure

- `skills/` — individual skill packages
- `scripts/` — deploy and maintenance scripts

## Principles

- Develop skills here, not directly inside `~/.openclaw/skills`
- Treat `~/.openclaw/skills` as install/runtime target
- Keep each skill self-contained
- Avoid absolute machine-specific paths
