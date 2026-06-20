---
name: feishu-task-notifier
description: Use when the user explicitly asks for a Feishu notification, Feishu reminder, Feishu push, or notification after a task completes.
---

# Feishu Task Notifier

Send a short Feishu notification through the user's dedicated cc-connect
notification bot. Use this only for explicit Feishu notification requests.

Do not send a notification just because a task is complete, and do not use this
for ordinary final replies or status updates unless the user explicitly asks.

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
