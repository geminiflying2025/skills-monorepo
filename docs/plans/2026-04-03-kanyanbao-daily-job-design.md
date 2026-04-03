# Kanyanbao 单任务定时方案设计

## 目标

- 用一个系统定时任务完成看研报的昨日下载。
- 任务顺序固定为：复用登录态、下载昨日报告、同步到挂载盘、输出汇总。
- 避免 Codex 自动化沙箱对登录和 `/Volumes` 同步的干扰。

## 方案

- 新增总控脚本 [`scripts/kanyanbao_daily_job.sh`](/Users/macmini/Projects/skills-monorepo/scripts/kanyanbao_daily_job.sh) 作为唯一入口。
- 总控脚本默认允许交互式登录刷新；如果登录态失效，会调用 [`scripts/kanyanbao_refresh_state.sh`](/Users/macmini/Projects/skills-monorepo/scripts/kanyanbao_refresh_state.sh) 拉起浏览器补登录后继续。
- 如需显式关闭交互刷新，可设置环境变量 `KANYANBAO_ALLOW_INTERACTIVE_REFRESH=0`。
- 系统定时由 `launchd` 使用一个 plist 调度总控脚本。

## 关键权衡

- 优点：只有一个系统任务，运维面最小；下载和同步都在系统权限下执行，不受 Codex 沙箱限制。
- 限制：登录刷新仍然是交互式浏览器流程，所以调度触发时如果登录态失效，会拉起浏览器并等待人工完成登录确认。
- 结论：当前设计优先“自动补登录能力”而不是“完全无人值守”；如果后续需要彻底无人值守，需要再把登录刷新改成无头方案。

## 验证

- 新增测试覆盖总控脚本默认参数、昨日日期、以及交互刷新开关行为。
- 总控脚本复用现有下载脚本输出 JSON，便于日志采集和后续告警。
