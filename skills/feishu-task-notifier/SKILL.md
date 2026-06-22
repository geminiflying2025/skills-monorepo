---
name: feishu-task-notifier
description: Use when the user explicitly includes the exact phrase "飞书通知" and asks to send that notification.
---

# Feishu Task Notifier

Send a short Feishu notification through the user's dedicated cc-connect
notification bot.

## Strict Trigger Rule

Use this skill only when the user's request explicitly includes the exact phrase
`飞书通知`.

Do not use this skill for broader requests such as `通知我`, `发个通知`,
`提醒我`, `Feishu notification`, `Feishu reminder`, `Feishu push`, task-complete
notifications, ordinary final replies, or status updates unless the request
also says `飞书通知`.

## Command

Resolve `<skill-dir>` to the directory containing this `SKILL.md`.

Required runtime configuration:

- `CC_FEISHU_NOTIFY_CONFIRM=1`
- `CC_NOTIFY_SESSION`: target cc-connect Feishu session key
- `CC_NOTIFY_PROJECT`: cc-connect project name, defaults to `codex-feishu-notify`

Use the packaged script directly:

```bash
CC_FEISHU_NOTIFY_CONFIRM=1 \
CC_NOTIFY_SESSION='feishu:<chat-or-scope>:<user>' \
<skill-dir>/scripts/feishu-notify "任务完成：简短说明"
```

For long or multi-line messages:

```bash
cat <<'EOF' | CC_FEISHU_NOTIFY_CONFIRM=1 \
CC_NOTIFY_SESSION='feishu:<chat-or-scope>:<user>' \
<skill-dir>/scripts/feishu-notify
任务完成：简短标题

- 结果：...
- 路径：...
- 需要用户处理：...
EOF
```

If the deployed environment wants a shorter command, symlink the packaged script
into a directory on `PATH`. Keep machine-local session keys in environment
variables, not in this skill package.

## Message Style

Keep notifications short and actionable. Include:

- task/result summary
- important path, URL, or command if relevant
- whether user action is needed

Do not include secrets, tokens, cookies, `.env` values, or raw credentials.
