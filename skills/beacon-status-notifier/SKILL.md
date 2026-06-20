---
name: beacon-status-notifier
description: Use when the user explicitly asks to notify them through Beacon with the current Codex or agent execution status.
---

# Beacon Status Notifier

Send a Beacon reminder containing the current execution status. Use this only
when the user explicitly asks for a Beacon notification, reminder, or current
status push.

Do not use for ordinary progress updates, summaries, final replies, or routine
implementation work.

## Configuration

Set `BEACON_ACCESS_KEY` in one of:

- environment variables
- the current working directory `.env`
- `<skill-dir>/.env`

Example:

```env
BEACON_ACCESS_KEY=beacon_xxx
```

Do not commit real access keys. Use `<skill-dir>/.env.example` as the template.

## API Contract

- Base URL: `https://www.edgevix.com/beacon-api`
- Endpoint: `POST /reminders`
- External calls must not add another `/api` path segment.
- Authentication: `Authorization: Bearer <BEACON_ACCESS_KEY>`
- Required payload fields used here: `title`, `body`, `deadline`,
  `anchor_timezone`, `mode`, `kind`, `source_name`

## Workflow

1. Summarize the current execution status in one concise sentence or short
   paragraph.
2. Resolve `<skill-dir>` to the directory containing this `SKILL.md`.
3. Run `scripts/send_status.py` with that status text.
4. Report whether Beacon accepted the reminder. Do not print the access key.

Example:

```bash
python3 <skill-dir>/scripts/send_status.py \
  "Codex has finished the TestFlight upload; App Store Connect is processing the build."
```

For validation without sending or requiring `BEACON_ACCESS_KEY`:

```bash
python3 <skill-dir>/scripts/send_status.py \
  --dry-run "Dry-run status check."
```
