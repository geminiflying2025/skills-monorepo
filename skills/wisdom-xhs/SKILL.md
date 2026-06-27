---
name: wisdom-xhs
description: Use when tasks involve 小红书笔记读取、搜索、详情、评论、图文发布、视频发布、账号状态检查.
---

# XiaoHongShu Reader And Publisher

Use this skill when the user wants to read or publish XiaoHongShu content in a
single workflow.

This skill assumes the local stack is:

- `mcporter`
- `xiaohongshu-mcp-node` configured as mcporter server `xiaohongshu`
- Python Playwright only for the QR login helper

Older `agent-reach` / Docker / `xiaohongshu-mcp` setups can still work as a
legacy fallback, but they are not the default for this machine.

The helper scripts in this skill auto-detect the user-level `mcporter`
configuration file, typically `~/.mcporter/mcporter.json` or
`~/config/mcporter.json`.

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

- `mcporter_installed`
- `xiaohongshu_mcp_node_installed`
- `domestic_xiaohongshu_mcp_configured`
- `cookies_path`
- `cookies_file_exists`
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

The wrapper accepts old snake_case arguments and maps them to the domestic MCP
camelCase names (`feed_id` -> `feedId`, `xsec_token` -> `xsecToken`,
`load_all_comments` -> `loadAllComments`). It also maps old tool names such as
`publish_with_video` to `publish_video`.

## Login

### Preferred: QR login with persistent wait

```bash
python3 <skill-dir>/scripts/xhs_login_wait.py \
  --qr-output /abs/path/to/output/xiaohongshu-login/qr.png \
  --timeout-seconds 240
```

This opens the XiaoHongShu login page, saves the QR image if requested, waits
for the user to scan it, then writes Playwright cookies to:

- `$COOKIES_PATH`, if set
- otherwise `~/Library/Application Support/wisdom-xhs/cookies-node.json`

Do not print or commit cookie contents.

### One-shot MCP QR is diagnostic only

```bash
mcporter call xiaohongshu.get_login_qrcode
mcporter call xiaohongshu.check_login_status
```

For stdio MCP servers, this one-shot call can return a QR image and then exit
before the background login wait saves cookies. Use `xhs_login_wait.py` when
login persistence matters.

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

### Direct Playwright fallback when MCP list/search times out

If `list_feeds` or `search_feeds` times out but `check_login_status` is logged
in, use the direct reader. It reuses the saved cookies, opens XiaoHongShu with
Python Playwright, clicks a visible search card, and writes JSON + Markdown +
screenshot artifacts.

```bash
python3 <skill-dir>/scripts/xhs_direct_read.py \
  --search-keyword AI \
  --search-index 0 \
  --output-dir /abs/path/to/output/xiaohongshu
```

For a note URL that already includes `xsec_token`, or an `xhslink.com` short
share URL:

```bash
python3 <skill-dir>/scripts/xhs_direct_read.py \
  --url "http://xhslink.com/o/<share-id>" \
  --output-dir /abs/path/to/output/xiaohongshu
```

The direct reader records `media_type` as `image`, `video`, or `unknown`, plus
image URLs, video element URLs when exposed by the browser, focused text, and a
page screenshot.

### Note detail

Use `feed_id` and `xsec_token` returned by feed list or search:

```bash
mcporter call xiaohongshu.get_feed_detail \
  feedId=<feed-id> \
  xsecToken=<xsec-token>
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

### Auto classify from URL, then dispatch to the right summarizer

For a full XiaoHongShu URL, first read note detail and classify the note type.

- If it is a video note: extract audio, transcribe full audio text, and output
  merged corpus (`title + desc + transcript`) without time slicing.
- If it is a non-video note: automatically fall back to main-content summary +
  image OCR.

### Structured refinement requirement (新增结构化提炼要求)

For video summary outputs, besides merged corpus, you should also generate a
structured refinement artifact for easier downstream reuse.

Important:

- Structured refinement should be generated by the skills caller (LLM in-session).
- Do not rely on external LLM APIs as a hard requirement.
- Script-side rule extraction can exist as draft fallback, but caller-generated
  summary is preferred output for final delivery.

Required sections:

- `主题一句话` (one-line theme)
- `关键要点` (3-8 bullets)
- `片单结构化` (ranked item list when detectable)
- `可复用文案` (short reusable copy snippet)

Recommended output files:

- `feed-<id>-video-summary.md`
- `feed-<id>-video-summary.json`

If ranked items cannot be reliably extracted from transcript, keep the
`片单结构化` section and explicitly mark it as `未稳定识别`.

```bash
python3 <skill-dir>/scripts/xhs_summarize_video.py \
  --xhs-url "https://www.xiaohongshu.com/..." \
  --output-dir /abs/path/to/output/xiaohongshu
```

This is the preferred entrypoint when the user gives you a shared XiaoHongShu
link and you do not yet know whether it is 图文 or 视频.

### Video only: local file or direct media URL

If you already have a local video file:

```bash
python3 <skill-dir>/scripts/xhs_summarize_video.py \
  --video-file /abs/path/to/video.mp4 \
  --output-dir /abs/path/to/output/xiaohongshu
```

Load more comments when useful:

```bash
mcporter call xiaohongshu.get_feed_detail \
  feedId=<feed-id> \
  xsecToken=<xsec-token> \
  loadAllComments=true
```

### User profile

The domestic `xiaohongshu-mcp-node` package currently does not expose a
`user_profile` tool through mcporter. If an older server exposes it, call it
through `xhs_call.py` and save the raw result.

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
mcporter call xiaohongshu.publish_video \
  title="标题" \
  content="正文内容" \
  video=/abs/path/video.mp4 \
  tags=标签1,标签2
```

## Interaction Commands

### Comment

```bash
mcporter call xiaohongshu.post_comment \
  feedId=<feed-id> \
  xsecToken=<xsec-token> \
  content="评论内容"
```

### Like / Favorite

```bash
mcporter call xiaohongshu.like_feed \
  feedId=<feed-id> \
  xsecToken=<xsec-token>
```

```bash
mcporter call xiaohongshu.favorite_feed \
  feedId=<feed-id> \
  xsecToken=<xsec-token>
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
