---
name: wisdom-x-trends
description: 抓取并聚合 X/Twitter 热点。用于“看 X 上最近什么最热”“按财经/科技/AI/经济/地区冲突抓热点”“输出事件级热点清单”这类请求。默认主题为财经、科技、AI、经济、地区冲突，支持自定义主题与查询词。
---

# Wisdom X Trends

按下面顺序执行，不要跳步。

## 1) 适用范围

适合：

- 从 X/Twitter 发现热点事件
- 按主题抓热点而不是只搜单条帖子
- 输出可给 news / marketing agent 继续消费的结构化热点清单

默认主题：

- finance
- tech
- ai
- economy
- regional-conflicts

支持用户额外指定主题或直接传原始查询词。

## 2) 前置检查

先确认：

- `xreach` 可执行
- `xreach` 已登录

如果未登录，直接提示：

```bash
xreach auth extract --browser chrome
```

如果环境里实际提示的是 `xfetch`，也可以执行：

```bash
xfetch auth extract --browser chrome
```

如果浏览器里还没登录 X，先让用户在浏览器登录后再执行。

## 3) 首选入口

开发阶段默认把产物落到仓库 `output/x-trends/`：

```bash
python3 <skill-dir>/scripts/x_trends.py \
  --output-dir /abs/path/to/output/x-trends
```

带自定义主题：

```bash
python3 <skill-dir>/scripts/x_trends.py \
  --topics finance,ai,regional-conflicts \
  --output-dir /abs/path/to/output/x-trends
```

带原始查询：

```bash
python3 <skill-dir>/scripts/x_trends.py \
  --query "OpenAI OR Anthropic OR Gemini" \
  --query "tariffs OR bond yields OR inflation" \
  --output-dir /abs/path/to/output/x-trends
```

## 4) 输出要求

脚本输出四类产物：

- `x-trends-raw.json`
- `x-trends-hotspots.json`
- `x-trends-hotspots.md`
- `x-trends-briefing.json`

热点结果要是事件级，不是简单 tweet 列表。

每个热点至少包含：

- 主题
- 英文事件标题
- 关键词
- 代表性 tweet
- 热度分
- 时间信息

其中 `x-trends-briefing.json` 是给大模型二次总结用的精简语料。
拿到它以后，应由当前大模型统一输出中文热点简报，而不是依赖脚本直译。
中文简报里要明确：

- 可信度
- 核实状态
- 是否建议纳入正式简报

## 5) 使用边界

- 这个技能只负责抓取、聚合、排序、落盘
- 自动过滤任何涉及中国国内政治环境或中国领导人讨论的话题与内容
- 不负责发送到 Telegram / Feishu / 邮件
- 不负责自动调度
- 不负责最终 AI 改写成口播稿或营销稿

## 6) 失败处理

- `xreach` 缺失：报安装问题
- `xreach` 未登录：报登录问题
- 单个 query 失败：保留其他 query 结果，并在输出里记录失败项
- 完全无结果：输出空结果文件，不要崩溃
- 如果所有 query 都因 X 登录态失败：直接报登录问题，不要伪装成“成功但没热点”

## 7) 频率建议

- 默认建议每 4 小时跑 1 次
- 事件窗口期可临时提高到每 2-3 小时 1 次
- 不建议长期每小时跑一次，容易触发 X 风控

## 8) 最终中文输出模版

统一按下面结构输出，不要自由发挥版式：

```markdown
# X 热点中文简报
生成时间：{datetime}
主题范围：{topics}

## 总览
- 本轮共发现 {n} 条热点
- 已核实：{a} 条
- 部分核实：{b} 条
- 未核实：{c} 条

## 建议优先关注
{只放高可信或建议纳入正式简报的 3-5 条}

## 热点明细

### 1. {中文热点标题}
- 主题：{财经 / 科技 / AI / 经济 / 地区冲突 / 自定义}
- 可信度：{高 / 中 / 低}
- 核实状态：{已核实 / 部分核实 / 未核实}
- 是否纳入正式简报：{建议纳入 / 标注后纳入 / 暂不纳入}
- 热度分：{score}
- 最新时间：{time}

摘要：
{1-2句中文摘要，说明发生了什么。}

为什么值得关注：
{1-2句中文解释，对市场、行业、舆论或业务的意义。}

核实说明：
{说明是否有主流媒体/官方源支持；如果没有，要明确写“主要来自 X 平台讨论，尚待进一步核实”。}

代表信息源：
- X：{representative_post_url}
- 验证来源：
  - {source_1}
  - {source_2}

## 待核实线索
{只列低可信但有传播热度的内容，短一点}

## 一句话结论
{总结本轮最核心的主线}
```

写作约束：

- 标题必须是自然中文，不直译英文原帖
- 摘要只写事件，不复述情绪化措辞
- 未核实内容必须显式标注，不能写得像确定事实
- 明显营销帖、喊单帖、情绪化帖子应放到“待核实线索”或直接跳过
