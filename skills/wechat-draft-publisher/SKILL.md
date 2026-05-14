---
name: wechat-draft-publisher
description: Use when creating or updating a WeChat Official Account article draft from local HTML, Markdown-rendered HTML, or Codex-generated article assets. Trigger on 微信公众号, 公众号草稿, WeChat draft, draft/add, AppID, AppSecret, thumb_media_id, or media_id.
---

# WeChat Draft Publisher

## Purpose

Publish a Codex-generated article to a WeChat Official Account draft. The skill creates drafts only; it does not mass-send or publish to followers.

## When To Use

- User asks to publish an article to 微信公众号草稿箱.
- User has local article HTML and image assets.
- User wants a repeatable Codex workflow for web article + WeChat draft publishing.

Do not use for 小红书, Twitter/X, newsletters, or final WeChat mass-send.

## Safety Rules

- Never ask the user to paste `WECHAT_APP_SECRET` into chat. Ask them to save it locally.
- If the secret appears in chat, do not repeat it. Recommend rotating it after testing.
- Default action is creating a draft. Never call a mass-send endpoint.
- Confirm before creating a new draft if the previous step was only a dry run.
- Use small JPEG/PNG images for WeChat; avoid uploading multi-megabyte generated originals.

## Required Inputs

- HTML file for the WeChat article body.
- Cover image path.
- Title.
- Optional author and summary.
- WeChat credentials in one of:
  - environment variables: `WECHAT_APP_ID`, `WECHAT_APP_SECRET`
  - project file: `.wechat-draft.env`
  - user file: `~/.wechat-draft.env`

Credential file format:

```env
WECHAT_APP_ID=wx...
WECHAT_APP_SECRET=...
```

## Recommended Workflow

1. Create a WeChat-specific HTML file with inline styles.
   - Do not rely on `<head>` CSS.
   - Keep layout simple: headings, paragraphs, blockquotes, bordered callouts, and images.
   - Use local image paths in `<img src="...">`.
2. Create small WeChat images.
   - Recommended widths: cover and landscape images `900px`, vertical infographics `720px`.
   - Recommended formats: `.jpg` or `.png`.
3. Run a dry run.
4. Confirm with the user.
5. Create the draft.
6. Report `media_id` and tell the user to check `内容管理 -> 草稿箱`.

## Commands

Resolve `<skill-dir>` to the directory containing this `SKILL.md`.

Dry run:

```bash
node <skill-dir>/scripts/publish-wechat-draft.mjs \
  --html /path/to/article-wechat.html \
  --title "标题" \
  --summary "摘要" \
  --author "作者" \
  --cover /path/to/cover.jpg \
  --dry-run
```

Create draft:

```bash
node <skill-dir>/scripts/publish-wechat-draft.mjs \
  --html /path/to/article-wechat.html \
  --title "标题" \
  --summary "摘要" \
  --author "作者" \
  --cover /path/to/cover.jpg
```

## WeChat API Notes

- Access token endpoint: `cgi-bin/token`.
- Permanent image material endpoint: `cgi-bin/material/add_material?type=image`.
- Draft endpoint: `cgi-bin/draft/add`.
- For normal article drafts, send `article_type: "news"` and `thumb_media_id`.
- The script uploads each local `<img>` and replaces the `src` with the returned WeChat image URL.
- The script sets `need_open_comment: 1` and `only_fans_can_comment: 0`.
- If access token fails with IP whitelist errors, ask the user to add the current API caller's public IP in `设置与开发 -> 基本配置 -> IP 白名单`.

## Output

Return:

- Input HTML path.
- Title and image count.
- Draft `media_id`.
- Whether it was a dry run or real draft creation.
- Reminder that the user should preview the draft before publishing.
