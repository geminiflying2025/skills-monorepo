---
name: readurl
description: Read URL content with anti-bot fallbacks (local Playwright snapshot, browser rendering, optional pagecopy mirror). Use when normal fetch misses content or hits JS/challenge pages.
---

# Webpage Reader (Stealth)

Use this skill when standard URL reads fail or return challenge pages.

## Execution Order (must follow)

1. **Local browser snapshot first (default)**
   - Use script: `scripts/local_snapshot.py`.
   - It renders the page locally with Playwright and saves HTML to local disk only.

2. **Direct fetch fallback**
   - Use `web_fetch` for quick extraction.
   - If output is complete and readable, stop.

3. **Browser rendering fallback**
   - Use `browser` to open/snapshot the page and read rendered DOM content.
   - Prefer user-attached Chrome profile when anti-bot depends on real session/cookies.

4. **Optional PageCopy service fallback (强制浏览器渲染镜像)**
   - Use script: `scripts/pagecopy_read.py` when local path still fails.
   - It calls `http://www.chenchen.city/pagecopy/api/snapshots` with `force_browser=true`, then pulls mirrored HTML and extracts readable text.

## Commands

Local-only (preferred):

```bash
python3 ~/.openclaw/skills/readurl/scripts/local_snapshot.py "<url>"
```

Optional local output dir:

```bash
python3 ~/.openclaw/skills/readurl/scripts/local_snapshot.py "<url>" \
  --out-dir "~/.openclaw/pagecopy-local"
```

Optional PageCopy service fallback:

```bash
python3 ~/.openclaw/skills/readurl/scripts/pagecopy_read.py "<url>" \
  --base "http://www.chenchen.city/pagecopy" \
  --force-browser
```

Optional PageCopy real URL with local images:

```bash
python3 ~/.openclaw/skills/readurl/scripts/pagecopy_read.py "<url>" \
  --base "http://www.chenchen.city/pagecopy" \
  --force-browser \
  --localize-images \
  --out-dir "$(pwd)/tmp/readurl-snapshots"
```

Use `--localize-images` when the mirrored PageCopy `archived_url` preserves text
layout but WeChat images stay in a loading state. The script keeps the original
`<base>` URL so WeChat CSS and layout resources continue to resolve correctly,
then rewrites WeChat image `src` / `data-src` values to absolute `file://` URLs
for downloaded local assets. Do not rewrite `<base>` to a local directory; that
fixes images but can break the real page styling.

Optional cookie header for session-gated pages:

```bash
python3 ~/.openclaw/skills/readurl/scripts/pagecopy_read.py "<url>" \
  --cookie "name=value; name2=value2" \
  --force-browser
```

## Output contract

Return:
- `archived_url`
- extracted plain text body
- when `--localize-images` is used: `localization.local_html_path`, `assets_dir`, `manifest_path`, and image counts
- warning if text looks incomplete (challenge/login/paywall)

If all fallbacks fail, explain exactly which layer failed and what user action is needed (e.g. provide cookies or attach Chrome tab).
