# Learnings Log

Captured learnings, corrections, and discoveries. Review before major tasks.

---

## 2026-03-26 | skills-monorepo | 命令参数规范
- 场景：部署或脚本命令执行前
- 学习：先运行 `--help` 或查看 README，再拼参数
- 结果：减少无效重试和参数拼写错误
- 规则：不确定参数时，先查再跑

## 2026-03-26 | skills-monorepo | 目录定位规范
- 场景：查找 skill 安装位置
- 学习：优先用真实安装路径，不假设统一在 `~/.openclaw/skills`
- 结果：避免“已安装但找不到”的误判
- 规则：先 `clawhub list`，再检查实际目录
