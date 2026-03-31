# Kanyanbao Cookie Usage

This note explains how other agents or tools should reuse the current Kanyanbao login state.

## State file

Current browser session state is usually exported to:

`/tmp/kanyanbao-state-now.json`

This is a Playwright `storageState` file. It contains:

- `cookies`
- `origins.localStorage`

## Important caveat

Do **not** assume this site works with a single `JSESSIONID`.

Kanyanbao uses multiple cookies with the same name but different paths, for example:

- `JSESSIONID` for `/`
- `JSESSIONID` for `/newsadapter`
- `JSESSIONID` for `/imageserver`

If a tool naively loads the JSON into a normal cookie jar and lets the HTTP client choose for you, requests may fail with:

- `check_session_status: 0`
- `登录状态失效`

Even when the browser session is still valid.

## Recommended approach

When sending HTTP requests outside Playwright:

1. Read cookies from `/tmp/kanyanbao-state-now.json`
2. Build the `Cookie` header manually for the target URL
3. For cookies with the same name, prefer the cookie whose `path` is the longest matching prefix of the request path
4. Send a browser-like header set

Recommended headers:

```text
Referer: https://www.kanyanbao.com/newreport/newReportSearch.htm
User-Agent: Mozilla/5.0
Accept: application/json, text/javascript, */*; q=0.01
X-Requested-With: XMLHttpRequest
```

For direct file downloads, `Accept: */*` is also fine.

## Path mapping

Use the cookie that matches the request path:

- Requests to `/newreport/...` should use the `/` session cookie
- Requests to `/newsadapter/...` should use the `/newsadapter` session cookie
- Requests to `/imageserver/...` should use the `/imageserver` session cookie
- `REPORT_SESSION_COOKIE` on `/` should also be included where applicable

## Playwright usage

If another agent is using Playwright, the easiest option is to reuse the state file directly:

```js
const context = await browser.newContext({
  storageState: "/tmp/kanyanbao-state-now.json",
});
```

This is more reliable than reconstructing cookies manually.

## Python example

This is the safe pattern for non-browser requests:

```python
import json
from pathlib import Path
from urllib.parse import urlparse

import requests


def build_cookie_header(cookies, url):
    parsed = urlparse(url)
    req_host = parsed.hostname or ""
    req_path = parsed.path or "/"

    chosen = {}
    for c in cookies:
        domain = str(c.get("domain") or "")
        path = str(c.get("path") or "/")
        name = str(c.get("name") or "")
        value = str(c.get("value") or "")
        if not name:
            continue

        domain_ok = req_host == domain.lstrip(".") or req_host.endswith(domain)
        path_ok = req_path.startswith(path)
        if not (domain_ok and path_ok):
            continue

        current = chosen.get(name)
        if current is None or len(path) >= len(current[0]):
            chosen[name] = (path, value)

    return "; ".join(f"{name}={value}" for name, (_path, value) in chosen.items())


state = json.loads(Path("/tmp/kanyanbao-state-now.json").read_text())
cookies = state["cookies"]
url = "https://www.kanyanbao.com/newreport/getNewDocColumns.json?isApp=false"

headers = {
    "Referer": "https://www.kanyanbao.com/newreport/newReportSearch.htm",
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": build_cookie_header(cookies, url),
}

resp = requests.get(url, headers=headers, timeout=60)
print(resp.status_code)
print(resp.text[:200])
```

## Session freshness

This file is temporary and may expire at any time.

If requests start returning login-expired responses:

1. Reopen the site in a real browser
2. Log in again
3. Re-export the session to `/tmp/kanyanbao-state-now.json`

The downloader now performs this check as its first step. It validates the
current state against the columns endpoint, and if the session is invalid it
launches [`scripts/kanyanbao_refresh_state.sh`](/Users/macmini/Projects/skills-monorepo/scripts/kanyanbao_refresh_state.sh)
before continuing.

## Current script reference

The current implementation that already handles this correctly is:

[`scripts/kanyanbao_search_download.py`](/Users/macmini/Projects/skills-monorepo/scripts/kanyanbao_search_download.py)
