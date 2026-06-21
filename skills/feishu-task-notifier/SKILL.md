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

Prefer the short command when available:

```bash
feishu-notify "任务完成：简短说明"
```

For long or multi-line messages:

```bash
cat <<'EOF' | feishu-notify
任务完成：简短标题

- 结果：...
- 路径：...
- 需要用户处理：...
EOF
```

If `feishu-notify` is not in `PATH`, use the deployed environment's configured
notification script. Do not hardcode a machine-local fallback path in this skill
package.

## Message Style

Keep notifications short and actionable. Include:

- task/result summary
- important path, URL, or command if relevant
- whether user action is needed

Do not include secrets, tokens, cookies, `.env` values, or raw credentials.
