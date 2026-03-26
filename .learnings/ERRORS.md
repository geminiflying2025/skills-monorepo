# Errors Log

Command failures, exceptions, and unexpected behaviors.

---

## 2026-03-26 | skills-monorepo | skill 目录误判
- 命令：`ls ~/.openclaw/skills/self-improving-agent`
- 报错/现象：目录不存在
- 根因：实际安装在 `~/Documents/OpenClaw/workspaces/main/skills/`
- 处理：改用真实路径继续配置
- 结论：先确认安装清单和实际路径再执行后续操作

## 2026-03-26 | skills-monorepo | 批量命令被策略拦截
- 命令：包含清理动作的多步 shell 脚本
- 报错/现象：`blocked by policy`
- 根因：命令中含删除/覆盖类高风险操作
- 处理：拆分为更安全的增量命令逐步执行
- 结论：优先使用最小变更命令，必要时分步执行
