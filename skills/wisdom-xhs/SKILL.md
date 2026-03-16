---
name: wisdom-xhs
description: Read and publish XiaoHongShu content through Agent Reach + mcporter + xiaohongshu-mcp. Use when tasks involve 小红书笔记读取、搜索、详情、评论、图文发布、视频发布、账号状态检查.
---

# XiaoHongShu Reader And Publisher

Use this skill when the user wants to read or publish XiaoHongShu content in a
single workflow.

This skill assumes the local stack is:

- `agent-reach`
- `mcporter`
- Docker
- `xiaohongshu-mcp`

The runtime target is `mcporter` server name `xiaohongshu`.

The helper scripts in this skill auto-detect the user-level `mcporter`
configuration file, typically `~/config/mcporter.json`.

## What This Skill Covers

- Check whether the XiaoHongShu stack is installed and connected
- Check login state
- Search notes
- Read note detail, comments, author profile
- Publish image posts
- Publish video posts

## Preferred Workflow

1. Check stack status first.
2. If not logged in, ask the user to log in with cookies or QR.
3. For reading:
   - start from `search_feeds` or `list_feeds`
   - then use `get_feed_detail`
4. For publishing:
   - confirm assets are on local disk
   - then use `publish_content` or `publish_with_video`

## Status Check

Resolve `<skill-dir>` to this skill directory, then run:

```bash
python3 <skill-dir>/scripts/xhs_stack_status.py
```

This prints JSON with:

- `agent_reach_installed`
- `mcporter_installed`
- `docker_installed`
- `docker_container_running`
- `mcporter_server_configured`
- `mcp_connected`
- `login_status`

## Generic MCP Caller

Use the wrapper when you want a stable way to call XiaoHongShu tools and save
results into the repo `output/` directory.

```bash
python3 <skill-dir>/scripts/xhs_call.py search_feeds \
  --arg keyword=AI工具 \
  --output /abs/path/to/output/xiaohongshu/search-ai-tools.json
```

```bash
python3 <skill-dir>/scripts/xhs_call.py get_feed_detail \
  --arg feed_id=<feed-id> \
  --arg xsec_token=<xsec-token> \
  --output /abs/path/to/output/xiaohongshu/feed-detail.json
```

## Login

### Preferred: Cookie import through Agent Reach

```bash
agent-reach configure xhs-cookies "key1=value1; key2=value2; ..."
```

Cookie source recommendation:

1. Log in to XiaoHongShu in your browser
2. Use Cookie-Editor
3. Export as Header String or JSON
4. Pass it to the command above

### Fallback: QR login

```bash
mcporter call xiaohongshu.get_login_qrcode
mcporter call xiaohongshu.check_login_status
```

## Reading Commands

### Login state

```bash
mcporter call xiaohongshu.check_login_status
```

### Home feed

```bash
mcporter call xiaohongshu.list_feeds
```

### Search

```bash
mcporter call xiaohongshu.search_feeds keyword=护肤
```

Optional filters can be passed through the raw MCP interface when needed.

### Note detail

Use `feed_id` and `xsec_token` returned by feed list or search:

```bash
mcporter call xiaohongshu.get_feed_detail \
  feed_id=<feed-id> \
  xsec_token=<xsec-token>
```

### Main content summary (no comments) + image OCR

Generate summary artifacts (JSON + Markdown) from note main content and image
OCR:

```bash
python3 <skill-dir>/scripts/xhs_summarize_main.py \
  --feed-id <feed-id> \
  --xsec-token <xsec-token> \
  --output-dir /abs/path/to/output/xiaohongshu
```

If you only want text metadata without OCR:

```bash
python3 <skill-dir>/scripts/xhs_summarize_main.py \
  --feed-id <feed-id> \
  --xsec-token <xsec-token> \
  --no-ocr
```

### Video: audio-only extraction and merged corpus

Extract audio, transcribe full audio text, and output merged corpus
(`title + desc + transcript`) without time slicing:

```bash
python3 <skill-dir>/scripts/xhs_summarize_video.py \
  --xhs-url "https://www.xiaohongshu.com/..." \
  --output-dir /abs/path/to/output/xiaohongshu
```

If you already have a local video file:

```bash
python3 <skill-dir>/scripts/xhs_summarize_video.py \
  --video-file /abs/path/to/video.mp4 \
  --output-dir /abs/path/to/output/xiaohongshu
```

Load more comments when useful:

```bash
mcporter call xiaohongshu.get_feed_detail \
  feed_id=<feed-id> \
  xsec_token=<xsec-token> \
  load_all_comments=true \
  limit=20 \
  scroll_speed=normal
```

### User profile

```bash
mcporter call xiaohongshu.user_profile \
  user_id=<user-id> \
  xsec_token=<xsec-token>
```

## Publish Commands

### Image post

```bash
mcporter call xiaohongshu.publish_content \
  title="标题" \
  content="正文内容" \
  images=/abs/path/1.jpg,/abs/path/2.jpg \
  tags=标签1,标签2
```

Notes:

- `images` must be absolute local paths or supported remote image URLs
- keep the title short enough for XiaoHongShu limits

### Video post

```bash
mcporter call xiaohongshu.publish_with_video \
  title="标题" \
  content="正文内容" \
  video=/abs/path/video.mp4 \
  tags=标签1,标签2
```

## Interaction Commands

### Comment

```bash
mcporter call xiaohongshu.post_comment_to_feed \
  feed_id=<feed-id> \
  xsec_token=<xsec-token> \
  content="评论内容"
```

### Like / Favorite

```bash
mcporter call xiaohongshu.like_feed \
  feed_id=<feed-id> \
  xsec_token=<xsec-token>
```

```bash
mcporter call xiaohongshu.favorite_feed \
  feed_id=<feed-id> \
  xsec_token=<xsec-token>
```

## Output Convention

When saving reading or publishing results during development in this repo,
default to:

- `output/xiaohongshu/*.json`
- `output/xiaohongshu/*.txt`

Do not commit generated output files.

## Practical Guidance

- If `check_login_status` says not logged in, do not keep retrying content
  tools. Fix login first.
- For most note-reading flows, `search_feeds` or `list_feeds` is the entry
  point because they provide `feed_id` and `xsec_token`.
- Prefer the wrapper script when you want a persistent output artifact in the
  repo.
- For publishing, prefer local file paths over remote URLs when possible.
