#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date, timedelta
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.parse import urlparse
from urllib.parse import unquote

import requests

BASE = "https://www.kanyanbao.com"
COLUMNS_URL = f"{BASE}/newreport/getNewDocColumns.json?isApp=false"
SEARCH_URL = f"{BASE}/newsadapter/report/fulltext_report_search.json"
DOWNLOAD_URL = f"{BASE}/imageserver/report/download.htm?id={{objid}}"
DEFAULT_CAPTCHA_COMMAND = (
    "/Users/macmini/Projects/skills-monorepo/skills/captcha-solver/fix_download.sh "
    '"$CAPTCHA_URL"'
)
DEFAULT_COLUMNS = [
    "世界经济",
    "宏观经济运行",
    "金融工程专题",
    "期货报告",
    "政策点评",
    "策略专题",
    "数据点评",
    "策略周报",
    "定期报告(债券)",
    "量化投资",
]

# Alias: user-facing name -> required column/doctypes
ALIASES = {
    "定期报告(债券)": {
        "columns": ["债券研究"],
        "doctypes": ["定期报告"],
    }
}


@dataclass
class ResolvedFilters:
    column_ids: list[int]
    doctype_ids: list[int]
    found_names: list[str]
    not_found_names: list[str]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Search and download kanyanbao reports")
    p.add_argument("--keyword", default="", help="search keyword")
    p.add_argument(
        "--column",
        action="append",
        default=[],
        help="column/type filter name, can be repeated; each item also supports comma-separated names",
    )
    p.add_argument(
        "--columns",
        default="",
        help="(compat) comma-separated column/type names",
    )
    p.add_argument("--top", type=int, default=10, help="max downloadable reports")
    p.add_argument("--page-size", type=int, default=40, help="search page size")

    p.add_argument("--start", default="", help="start date YYYY-MM-DD")
    p.add_argument("--end", default="", help="end date YYYY-MM-DD")
    p.add_argument(
        "--last-days",
        type=int,
        default=None,
        help="recent N days. when absent and no start/end set, defaults to 7",
    )

    p.add_argument(
        "--state-file",
        default="/tmp/kanyanbao-state-now.json",
        help="playwright storageState json path",
    )
    p.add_argument("--output-dir", default="", help="output directory")
    p.add_argument(
        "--force-download",
        action="store_true",
        help="force redownload even if same objid file already exists in output dir",
    )
    p.add_argument(
        "--captcha-command",
        default=DEFAULT_CAPTCHA_COMMAND,
        help="command to run when a captcha page is detected; receives CAPTCHA_URL and DOWNLOAD_URL in env",
    )
    p.add_argument("--dry-run", action="store_true", help="only list results without downloading")
    return p.parse_args()


def split_list(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,，、\n]", raw)
    return [x.strip() for x in parts if x.strip()]


def collect_column_filters(args: argparse.Namespace) -> list[str]:
    out: list[str] = []
    for part in args.column:
        out.extend(split_list(part))
    out.extend(split_list(args.columns))

    # No filters passed means "all columns" (no doccolumn/doctypes constraint).
    if not out:
        return []

    # Explicit default keyword enables the preset 10-column bundle.
    lowered = [x.lower() for x in out]
    if "default" in lowered or "defaut" in lowered:
        out = [x for x in out if x.lower() not in {"default", "defaut"}]
        out.extend(DEFAULT_COLUMNS)
    # keep order, remove duplicates
    uniq: list[str] = []
    for x in out:
        if x not in uniq:
            uniq.append(x)
    return uniq


def sanitize_filename(name: str) -> str:
    n = unquote(name or "")
    n = n.replace("*", " ")
    n = re.sub(r"[\\/:*?\"<>|]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n[:120] if n else "未命名报告"


def resolve_date_range(args: argparse.Namespace) -> tuple[str, str, int]:
    if args.last_days is not None:
        if args.last_days < 1:
            raise ValueError("--last-days must be >= 1")
        end_d = date.today()
        start_d = end_d - timedelta(days=args.last_days - 1)
        return start_d.isoformat(), end_d.isoformat(), args.last_days

    if args.start and args.end:
        # Validate format
        _ = date.fromisoformat(args.start)
        _ = date.fromisoformat(args.end)
        return args.start, args.end, (date.fromisoformat(args.end) - date.fromisoformat(args.start)).days + 1

    if args.start or args.end:
        raise ValueError("--start and --end must be provided together")

    # Default behavior requested by user
    end_d = date.today()
    start_d = end_d - timedelta(days=6)
    return start_d.isoformat(), end_d.isoformat(), 7


def load_state_session(state_file: Path) -> requests.Session:
    if not state_file.exists():
        raise FileNotFoundError(f"state file not found: {state_file}")

    obj = json.loads(state_file.read_text(encoding="utf-8"))
    sess = requests.Session()
    for c in obj.get("cookies", []):
        sess.cookies.set(
            c["name"],
            c["value"],
            domain=c.get("domain"),
            path=c.get("path", "/"),
        )
    sess.headers.update(
        {
            "Referer": f"{BASE}/newreport/newReportSearch.htm",
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        }
    )
    # Keep original cookie records so we can reproduce browser-like cookie selection by path.
    setattr(sess, "_kanyanbao_state_cookies", obj.get("cookies", []))
    return sess


def build_cookie_header(cookies: list[dict[str, Any]], url: str) -> str:
    parsed = urlparse(url)
    req_host = parsed.hostname or ""
    req_path = parsed.path or "/"

    chosen: dict[str, tuple[str, str]] = {}
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


def state_get(session: requests.Session, url: str, **kwargs: Any) -> requests.Response:
    headers = dict(kwargs.pop("headers", {}) or {})
    state_cookies = getattr(session, "_kanyanbao_state_cookies", [])
    cookie_header = build_cookie_header(state_cookies, url)
    if cookie_header:
        headers["Cookie"] = cookie_header
    return session.get(url, headers=headers, **kwargs)


def build_captcha_url(download_url: str) -> str:
    parsed = urlparse(download_url)
    redirect_url = quote(parsed.path + (f"?{parsed.query}" if parsed.query else ""), safe="")
    return f"{BASE}/new/view/report/download_check.jsp?redirect_url={redirect_url}"


def is_captcha_page(response: requests.Response) -> bool:
    ct = (response.headers.get("content-type") or "").lower()
    if "text/html" not in ct:
        return False
    text = response.text[:5000]
    return (
        "报告下载验证" in text
        or "图形验证码" in text
        or "download_check.jsp" in text
    )


def fetch_columns(session: requests.Session) -> list[dict[str, Any]]:
    r = state_get(session, COLUMNS_URL, timeout=60)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("check_session_status") == 0:
        raise RuntimeError(data.get("message") or "login session expired")
    if not isinstance(data, list):
        raise RuntimeError("unexpected columns response")
    return data


def build_name_index(columns_data: list[dict[str, Any]]) -> dict[str, list[tuple[str, int]]]:
    idx: dict[str, list[tuple[str, int]]] = {}

    def put(name: str, kind: str, idv: int) -> None:
        if not name:
            return
        idx.setdefault(name, []).append((kind, int(idv)))

    for col in columns_data:
        put(col.get("name", ""), "column", col.get("id", 0))
        for sub in col.get("subs", []) or []:
            put(sub.get("name", ""), "subcolumn", sub.get("id", 0))
            for t in sub.get("types", []) or []:
                put(t.get("name", ""), "doctype", t.get("id", 0))
        for t in col.get("types", []) or []:
            put(t.get("name", ""), "doctype", t.get("id", 0))
    return idx


def resolve_filters(raw_names: list[str], name_index: dict[str, list[tuple[str, int]]]) -> ResolvedFilters:
    expanded: list[str] = []
    for n in raw_names:
        if n in ALIASES:
            expanded.extend(ALIASES[n].get("columns", []))
            expanded.extend(ALIASES[n].get("doctypes", []))
        else:
            expanded.append(n)

    column_ids: set[int] = set()
    doctype_ids: set[int] = set()
    found: list[str] = []
    not_found: list[str] = []

    for n in expanded:
        pairs = name_index.get(n, [])
        if not pairs:
            not_found.append(n)
            continue
        found.append(n)
        for kind, idv in pairs:
            if kind in {"column", "subcolumn"} and idv > 0:
                column_ids.add(idv)
            elif kind == "doctype" and idv > 0:
                doctype_ids.add(idv)

    return ResolvedFilters(
        column_ids=sorted(column_ids),
        doctype_ids=sorted(doctype_ids),
        found_names=sorted(set(found), key=found.index),
        not_found_names=sorted(set(not_found), key=not_found.index),
    )


def build_search_params(
    keyword: str,
    start: str,
    end: str,
    page: int,
    page_size: int,
    column_ids: list[int],
    doctype_ids: list[int],
) -> dict[str, Any]:
    return {
        "starttime": start,
        "endtime": end,
        "page": page,
        "pageSize": page_size,
        "search": keyword,
        "notSearch": "",
        "doccolumns": ",".join(str(x) for x in column_ids),
        "doctypes": ",".join(str(x) for x in doctype_ids),
        "industrycodes": "",
        "brokers": "",
        "stkcodes": "",
        "analystIds": "",
        "searchSaveId": "",
        "pageNumStart": "",
        "mystock": "",
        "sortByPagenum": "false",
        "sortByHot": "false",
        "sortByTime": "true",
        "investrank": "",
        "industryrank": "",
        "marketOC": "false",
        "marketKCB": "false",
        "language": "",
        "clickFrom": 0,
        "hyperSearchField": "title",
        "seriesTitle": "",
        "j_captcha_response": "",
        "newsDealSpecialDocColumn": "true",
        "timeOut": 200,
    }


def search_reports(
    session: requests.Session,
    keyword: str,
    start: str,
    end: str,
    page_size: int,
    top: int,
    column_ids: list[int],
    doctype_ids: list[int],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen_obj_ids: set[int] = set()

    page = 1
    while len(out) < top and page <= 300:
        params = build_search_params(keyword, start, end, page, page_size, column_ids, doctype_ids)
        r = state_get(session, SEARCH_URL, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()

        reports = data.get("reports", []) or []
        attach_map = data.get("reportAttachMap", {}) or {}

        if not reports:
            break

        page_added = 0
        for rp in reports:
            if rp.get("type") != "REPORT":
                continue
            if not rp.get("downloadable", True):
                continue
            rid = str(rp.get("id"))
            attaches = attach_map.get(rid) or []
            if not attaches:
                continue
            first = attaches[0]
            objid = int(first.get("OBJID", 0))
            if objid <= 0 or objid in seen_obj_ids:
                continue
            seen_obj_ids.add(objid)

            title = re.sub(r"<[^>]+>", "", str(rp.get("title", ""))).strip()
            filetype = str(first.get("FILETYPE") or "pdf").lower()
            if filetype not in {"pdf", "doc", "docx", "xls", "xlsx"}:
                filetype = "pdf"

            out.append(
                {
                    "report_id": int(rid),
                    "objid": objid,
                    "title": title,
                    "attach_name": str(first.get("NAME") or ""),
                    "filetype": filetype,
                    "download_url": DOWNLOAD_URL.format(objid=objid),
                }
            )
            page_added += 1
            if len(out) >= top:
                break

        if page_added == 0 and len(reports) < page_size:
            break
        if len(reports) < page_size:
            break
        page += 1

    return out[:top]


def download_file(session: requests.Session, url: str, out_path: Path) -> tuple[bool, int, str]:
    try:
        r = state_get(session, url, timeout=120, headers={"Accept": "*/*", "X-Requested-With": ""})
        if is_captcha_page(r):
            return False, r.status_code, f"captcha_required:{build_captcha_url(url)}"
        ct = (r.headers.get("content-type") or "").lower()
        is_file = (
            r.status_code == 200
            and len(r.content) > 0
            and (
                "pdf" in ct
                or "word" in ct
                or "octet-stream" in ct
                or "spreadsheetml" in ct
                or "ms-excel" in ct
            )
        )
        if not is_file:
            return False, r.status_code, f"non_file:{ct[:80]}"
        out_path.write_bytes(r.content)
        return True, r.status_code, ""
    except Exception as e:  # noqa: BLE001
        return False, 0, str(e)


def find_existing_by_objid(output_dir: Path, objid: int) -> Path | None:
    # Existing files follow: "<index>_<title>_<objid>.<ext>"
    matches = list(output_dir.glob(f"*_{objid}.*"))
    return matches[0] if matches else None


def run_captcha_command(command: str, captcha_url: str, download_url: str) -> int:
    env = os.environ.copy()
    env["CAPTCHA_URL"] = captcha_url
    env["DOWNLOAD_URL"] = download_url
    proc = subprocess.run(command, shell=True, env=env, check=False)
    return int(proc.returncode)


def main() -> int:
    args = parse_args()
    state_file = Path(args.state_file)

    start, end, effective_days = resolve_date_range(args)

    columns_input = collect_column_filters(args)
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else Path("output") / f"kanyanbao-search-{(args.keyword or '全部').strip()}-{start}_to_{end}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    session = load_state_session(state_file)
    columns_data = fetch_columns(session)
    name_index = build_name_index(columns_data)
    resolved = resolve_filters(columns_input, name_index)

    results = search_reports(
        session=session,
        keyword=args.keyword,
        start=start,
        end=end,
        page_size=args.page_size,
        top=args.top,
        column_ids=resolved.column_ids,
        doctype_ids=resolved.doctype_ids,
    )

    manifest: list[dict[str, Any]] = []
    skipped_existing = 0
    downloaded_new = 0
    captcha_required_count = 0
    captcha_urls: list[str] = []
    for i, item in enumerate(results, start=1):
        ext = item["filetype"] or "pdf"
        file_name = f"{i:02d}_{sanitize_filename(item['title'])}_{item['objid']}.{ext}"
        row = {
            "index": i,
            "report_id": item["report_id"],
            "objid": item["objid"],
            "title": item["title"],
            "file": file_name,
            "url": item["download_url"],
            "ok": False,
            "status": 0,
            "error": "",
        }

        if args.dry_run:
            row["ok"] = True
            row["status"] = 0
        else:
            existing = None if args.force_download else find_existing_by_objid(output_dir, item["objid"])
            if existing is not None:
                row["ok"] = True
                row["status"] = 208
                row["error"] = "skipped_existing"
                row["file"] = existing.name
                skipped_existing += 1
            else:
                ok, status, err = download_file(session, item["download_url"], output_dir / file_name)
                if (not ok) and err.startswith("captcha_required:"):
                    captcha_required_count += 1
                    captcha_url = err.split(":", 1)[1]
                    captcha_urls.append(captcha_url)
                    if args.captcha_command:
                        exit_code = run_captcha_command(args.captcha_command, captcha_url, item["download_url"])
                        if exit_code == 0:
                            session = load_state_session(state_file)
                            ok, status, err = download_file(session, item["download_url"], output_dir / file_name)
                row["ok"] = ok
                row["status"] = status
                row["error"] = err
                if ok:
                    downloaded_new += 1
        manifest.append(row)

    json_path = output_dir / "download_manifest.json"
    csv_path = output_dir / "download_manifest.csv"
    json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["index", "report_id", "objid", "title", "file", "url", "ok", "status", "error"],
        )
        w.writeheader()
        w.writerows(manifest)

    summary = {
        "keyword": args.keyword,
        "start": start,
        "end": end,
        "effective_days": effective_days,
        "input_columns": columns_input,
        "resolved_column_ids": resolved.column_ids,
        "resolved_doctype_ids": resolved.doctype_ids,
        "not_found_filters": resolved.not_found_names,
        "found_filters": resolved.found_names,
        "top": args.top,
        "matched": len(results),
        "downloaded_ok": sum(1 for x in manifest if x["ok"]),
        "downloaded_new": downloaded_new,
        "skipped_existing": skipped_existing,
        "download_failed": sum(1 for x in manifest if not x["ok"]),
        "captcha_required_count": captcha_required_count,
        "captcha_urls": captcha_urls,
        "output_dir": str(output_dir),
        "manifest_json": str(json_path),
        "manifest_csv": str(csv_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
