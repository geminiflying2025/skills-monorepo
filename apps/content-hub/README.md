# content-hub

轻量版统一内容处理 Hub，覆盖 `Collect -> Analyze -> Output` 闭环。

## 当前能力

- 输入：`url`、`rss`、`markdown`
- 分析：统一生成 `Analysis Package`
- 产物：`web`、`wechat`、`xhs`、`ppt`
- 入口：轻量 Web UI + CLI

## 运行

```bash
PYTHONPATH=apps/content-hub python -m content_hub.cli serve --port 8000
```

## CLI 示例

```bash
PYTHONPATH=apps/content-hub python -m content_hub.cli ingest --type markdown "# Demo\n\ncontent"
PYTHONPATH=apps/content-hub python -m content_hub.cli analyze 1
PYTHONPATH=apps/content-hub python -m content_hub.cli generate 1 --channel web
PYTHONPATH=apps/content-hub python -m content_hub.cli export 1
```
