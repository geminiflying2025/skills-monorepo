---
name: readurl
description: 综合读取 URL 内容并生成可供大模型总结的本地语料包。用于普通网页、反爬网页、需要浏览器渲染的页面、YouTube/Bilibili/小红书/微信短视频等视频链接、小宇宙等音频链接、小红书图文帖、X/Twitter 链接，以及需要下载原始媒体、抽取字幕、音频转写、关键帧截图、图片 OCR、失败跳过并记录整体执行情况的链接读取任务。
---

# ReadURL 综合链接读取

使用本 skill 时，目标不是直接替调用者完成最终摘要，而是尽可能把链接内容提取成本地语料包。最终总结、结构化提炼、事实判断由调用 skill 的大模型基于语料完成。

## 首选入口

解析 `<skill-dir>` 为本 skill 目录，然后运行：

```bash
python3 <skill-dir>/scripts/read_link.py "<url>" \
  --out-dir /abs/path/to/output/readurl
```

脚本会自动分类 URL，尽力提取：

- 网页正文
- `yt-dlp` 元数据与字幕
- 原始视频或音频（按参数选择）
- 图片与 OCR 文本（按参数选择）
- 关键帧截图（按参数选择）
- 失败阶段与错误原因

输出目录中固定生成：

- `result.json`：结构化结果、分类、元数据、产物路径、失败项
- `corpus.md`：给大模型阅读和总结的主语料
- `failures.json`：每个失败阶段，失败但可跳过的项目也要写入
- `web/`、`metadata/`、`media/`、`subtitles/`、`transcripts/`、`images/`、`ocr/`、`frames/`：按实际产物创建

如果处理多个 URL：

```bash
python3 <skill-dir>/scripts/read_link.py "<url1>" "<url2>" "<url3>" \
  --out-dir /abs/path/to/output/readurl
```

单个 URL 失败时不要中断整体任务；读取 `result.json` / `failures.json` 汇总成功与失败项。

## 固定运行时和缓存保护

运行 `readurl` 时必须固定一套 Python/Playwright 运行时。默认只使用当前 shell 的 `python3`，也就是 `which python3` 指向的解释器；不要临时改用 `/usr/bin/python3`、`/opt/homebrew/bin/python3`、`python3.12`、`npx playwright` 或 Node Playwright，除非任务明确要求并说明原因。

首次准备或修复 Playwright 环境时，在同一个 `python3` 下完成安装：

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

`yt-dlp` 也应安装到同一个默认 `python3` 环境，避免走 Homebrew Python 或系统 Python 后出现解析器依赖问题：

```bash
python3 -m pip install yt-dlp
python3 -m yt_dlp --version
```

`read_link.py` 调用 `local_snapshot.py` 时使用 `sys.executable`，所以启动 `read_link.py` 的解释器就是后续浏览器快照使用的解释器。遇到 “Playwright not installed” 或 “Please run playwright install” 时，先检查解释器和缓存路径：

```bash
which python3
python3 -c "import sys; print(sys.executable)"
python3 -m playwright --version
```

不要把“换一个 Python 跑”当成修复方式；根治方式是把依赖装到约定的同一个 `python3` 环境里。完成后用实际网页验证：

```bash
python3 <skill-dir>/scripts/local_snapshot.py https://example.com/ \
  --out-dir /abs/path/to/output/readurl/playwright-check \
  --timeout-seconds 20
```

如果 Playwright 自带 Chromium 缓存缺失，`local_snapshot.py` 会尝试使用 `PLAYWRIGHT_CHROMIUM_EXECUTABLE`、`CHROME_EXECUTABLE`，再回退到本机浏览器，例如 `/Applications/Google Chrome.app`。这只是运行时兜底，不代表可以随意删除 Playwright 缓存。

不要随意删除这些目录：

- `~/Library/Caches/ms-playwright`：macOS 上 Playwright 浏览器二进制默认缓存。
- `~/.cache/ms-playwright`：Linux 或设置 `PLAYWRIGHT_BROWSERS_PATH` 时常见的 Playwright 浏览器缓存。
- `~/.cache/uv`：`uv tool install` 和 Python 包下载缓存。
- `~/.local/share/uv/tools`：`uv tool install` 安装的工具环境，例如 `openai-whisper`。
- `~/.cache/yt-dlp` 或 `~/Library/Caches/yt-dlp`：`yt-dlp` 下载和提取器相关缓存。
- `~/.openclaw/skills/readurl`：已部署的 skill 运行时副本，不是普通缓存。

清理时不要使用 `rm -rf ~/Library/Caches/*`、`rm -rf ~/.cache/*` 这类大范围命令。必须清理时，先列出具体路径，并说明删除后需要重新安装或重新下载什么。

## 常用模式

### 普通网页 / 反爬网页

默认流程：

1. 直接 HTTP 抓取并抽正文
2. 本地 Playwright 快照：`scripts/local_snapshot.py`
3. PageCopy 服务强制浏览器渲染：`scripts/pagecopy_read.py`

```bash
python3 <skill-dir>/scripts/read_link.py "https://example.com/article" \
  --out-dir /abs/path/to/output/readurl
```

遇到需要人工登录、滑块或可见浏览器的页面：

```bash
python3 <skill-dir>/scripts/read_link.py "https://example.com/protected" \
  --local-headful \
  --out-dir /abs/path/to/output/readurl
```

如果需要 Cookie：

```bash
python3 <skill-dir>/scripts/read_link.py "https://example.com/protected" \
  --cookie "name=value; name2=value2" \
  --out-dir /abs/path/to/output/readurl
```

不要把 Cookie、Token 或其他密钥写进仓库、文档、提交信息或最终回复。

### 视频链接

适用于 YouTube、Bilibili、小红书视频、微信短视频、Douyin/TikTok 等 `yt-dlp` 支持或部分支持的链接。

先生成摘要语料（元数据 + 字幕；若无字幕会记录失败并继续）：

```bash
python3 <skill-dir>/scripts/read_link.py "<video-url>" \
  --out-dir /abs/path/to/output/readurl
```

下载原始视频：

```bash
python3 <skill-dir>/scripts/read_link.py "<video-url>" \
  --download-original \
  --max-download-mb 800 \
  --out-dir /abs/path/to/output/readurl
```

提取音频并尝试本地 Whisper 转写：

```bash
python3 <skill-dir>/scripts/read_link.py "<video-url>" \
  --extract-audio \
  --transcribe \
  --out-dir /abs/path/to/output/readurl
```

下载视频并抽关键帧：

```bash
python3 <skill-dir>/scripts/read_link.py "<video-url>" \
  --download-original \
  --capture-frames \
  --out-dir /abs/path/to/output/readurl
```

需要登录态的视频平台可优先使用浏览器 Cookie：

```bash
python3 <skill-dir>/scripts/read_link.py "<video-url>" \
  --cookies-from-browser chrome \
  --out-dir /abs/path/to/output/readurl
```

Bilibili 网页和 `yt-dlp` 可能返回 `HTTP Error 412: Precondition Failed`。遇到这种情况时，脚本会自动启用 Bilibili API fallback：先调用 `x/web-interface/view` 获取标题、UP 主、cid、统计和简介；如果传了 `--download-original` 或 `--capture-frames`，再调用 `x/player/playurl` 下载低清 mp4 并抽关键帧。

### 图文帖 / 小红书

通用入口会先尝试 `yt-dlp`，再回退到网页读取。对图文帖建议下载图片并 OCR：

```bash
python3 <skill-dir>/scripts/read_link.py "<xhs-url>" \
  --download-images \
  --ocr-images \
  --cookies-from-browser chrome \
  --out-dir /abs/path/to/output/readurl
```

如果当前环境已安装并配置 `wisdom-xhs`，小红书详情读取优先使用 `wisdom-xhs` 的 `xhs_summarize_main.py` / `xhs_summarize_video.py`；再把生成的正文、图片 OCR、音频转写结果纳入最终总结。

### 音频链接 / 小宇宙

先用 `yt-dlp` 抽取元数据、字幕或音频：

```bash
python3 <skill-dir>/scripts/read_link.py "<audio-url>" \
  --extract-audio \
  --transcribe \
  --out-dir /abs/path/to/output/readurl
```

如果没有本地 `whisper` 命令，脚本会保留音频文件并在 `failures.json` 中记录转写跳过；调用大模型可以改用其他转写工具继续处理。

### X / Twitter 链接

通用入口会先尝试 `yt-dlp` 抽媒体元数据/字幕，再回退到网页读取：

```bash
python3 <skill-dir>/scripts/read_link.py "https://x.com/user/status/123" \
  --cookies-from-browser chrome \
  --out-dir /abs/path/to/output/readurl
```

如果任务是 X 热点聚合而非读取单条链接，改用 `wisdom-x-trends`。

如果浏览器登录态或平台风控导致失败，记录失败项并继续处理其他 URL；不要伪造内容。

## 辅助脚本

`read_link.py` 会自动调用下列脚本。只有需要单独排障时才直接运行它们。

本地浏览器快照：

```bash
python3 <skill-dir>/scripts/local_snapshot.py "<url>" \
  --out-dir /abs/path/to/output/readurl/local-snapshot
```

PageCopy fallback：

```bash
python3 <skill-dir>/scripts/pagecopy_read.py "<url>" \
  --base "http://www.chenchen.city/pagecopy" \
  --force-browser
```

## 调用大模型的总结要求

读取完成后，调用者应打开 `corpus.md` 和必要的媒体产物进行总结。

建议输出：

- 内容一句话主题
- 关键要点
- 可复用摘录或结构化条目
- 证据来源：正文、字幕、转写、OCR、关键帧、元数据分别来自哪里
- 失败说明：哪些链接或阶段失败，是否影响结论

如果语料不足，例如只有标题和少量元数据，要明确写“语料不足，无法可靠总结”，不要补编。

## 失败处理

执行中任何单个阶段失败都应记录并继续：

- `yt-dlp` 不支持该站点：记录后回退网页读取
- 无字幕：记录后继续尝试音频、关键帧或网页正文
- 无本地 `whisper` / `tesseract` / `ffmpeg`：记录缺失工具并保留已有产物
- 需要登录或人工验证：记录需要用户提供登录态、Cookie 或可见浏览器操作
- 所有方式都失败：返回 `ok=false`，并报告每个失败阶段

最终回复必须说明：

- 成功读取了哪些链接和内容类型
- 生成了哪些本地产物
- 哪些阶段失败或跳过
- 后续若要补全，需要用户提供什么登录态、Cookie、工具或原始文件
