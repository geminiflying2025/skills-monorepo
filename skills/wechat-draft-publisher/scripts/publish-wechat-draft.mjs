#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token";
const UPLOAD_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material";
const DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/add";

function usage() {
  console.log(`Create a WeChat Official Account article draft.

Usage:
  node publish-wechat-draft.mjs --html article.html --title "Title" --cover cover.jpg [options]

Options:
  --html <path>       WeChat-compatible HTML file
  --title <text>      Article title
  --cover <path>      Cover image path
  --summary <text>    Digest/summary, max 120 chars recommended
  --author <text>     Author name
  --dry-run           Parse and validate only
  --help              Show help

Credentials:
  WECHAT_APP_ID and WECHAT_APP_SECRET from env, .wechat-draft.env, or ~/.wechat-draft.env
`);
}

function parseArgs(argv) {
  const args = { dryRun: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      usage();
      process.exit(0);
    }
    if (arg === "--dry-run") {
      args.dryRun = true;
      continue;
    }
    if (arg.startsWith("--")) {
      const key = arg.slice(2).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      const value = argv[i + 1];
      if (!value || value.startsWith("--")) {
        throw new Error(`Missing value for ${arg}`);
      }
      args[key] = value;
      i++;
    }
  }
  for (const key of ["html", "title", "cover"]) {
    if (!args[key]) throw new Error(`Missing required --${key}`);
  }
  return args;
}

function readEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return {};
  const out = {};
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx < 1) continue;
    const key = trimmed.slice(0, idx).trim();
    let value = trimmed.slice(idx + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

function loadConfig() {
  const cwdEnv = readEnvFile(path.resolve(".wechat-draft.env"));
  const homeEnv = readEnvFile(path.join(os.homedir(), ".wechat-draft.env"));
  const appId = process.env.WECHAT_APP_ID || cwdEnv.WECHAT_APP_ID || homeEnv.WECHAT_APP_ID;
  const appSecret = process.env.WECHAT_APP_SECRET || cwdEnv.WECHAT_APP_SECRET || homeEnv.WECHAT_APP_SECRET;
  if (!appId || !appSecret) {
    throw new Error("Missing WECHAT_APP_ID or WECHAT_APP_SECRET. Save them in env, .wechat-draft.env, or ~/.wechat-draft.env.");
  }
  return { appId, appSecret };
}

function resolveInput(filePath, baseDir = process.cwd()) {
  return path.isAbsolute(filePath) ? filePath : path.resolve(baseDir, filePath);
}

function extractBody(html) {
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  return (bodyMatch ? bodyMatch[1] : html).trim();
}

function imageRefs(html) {
  const refs = [];
  const imgRegex = /<img\b[^>]*\ssrc=["']([^"']+)["'][^>]*>/gi;
  for (const match of html.matchAll(imgRegex)) {
    refs.push({ fullTag: match[0], src: match[1] });
  }
  return refs;
}

async function fetchAccessToken(appId, appSecret) {
  const url = `${TOKEN_URL}?grant_type=client_credential&appid=${encodeURIComponent(appId)}&secret=${encodeURIComponent(appSecret)}`;
  const res = await fetch(url);
  const data = await res.json();
  if (data.errcode) throw new Error(`Access token error ${data.errcode}: ${data.errmsg}`);
  if (!data.access_token) throw new Error("No access_token in response");
  return data.access_token;
}

function mimeType(filename) {
  const ext = path.extname(filename).toLowerCase();
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".png") return "image/png";
  if (ext === ".gif") return "image/gif";
  if (ext === ".webp") return "image/webp";
  return "application/octet-stream";
}

async function uploadImage(imagePath, accessToken, baseDir) {
  let bytes;
  let filename;
  let type;

  if (/^https?:\/\//i.test(imagePath)) {
    const res = await fetch(imagePath);
    if (!res.ok) throw new Error(`Failed to download image ${imagePath}: ${res.status}`);
    bytes = Buffer.from(await res.arrayBuffer());
    filename = path.basename(new URL(imagePath).pathname) || "image.jpg";
    type = res.headers.get("content-type") || mimeType(filename);
  } else {
    const resolved = resolveInput(imagePath, baseDir);
    if (!fs.existsSync(resolved)) throw new Error(`Image not found: ${resolved}`);
    bytes = fs.readFileSync(resolved);
    filename = path.basename(resolved);
    type = mimeType(filename);
  }

  const form = new FormData();
  form.append("media", new Blob([bytes], { type }), filename);
  const url = `${UPLOAD_URL}?access_token=${encodeURIComponent(accessToken)}&type=image`;
  const res = await fetch(url, { method: "POST", body: form });
  const data = await res.json();
  if (data.errcode && data.errcode !== 0) throw new Error(`Upload failed ${data.errcode}: ${data.errmsg}`);
  if (!data.media_id && !data.url) throw new Error(`Unexpected upload response: ${JSON.stringify(data)}`);
  if (typeof data.url === "string") data.url = data.url.replace(/^http:\/\//i, "https://");
  return data;
}

async function uploadImagesInHtml(html, accessToken, baseDir) {
  let updated = html;
  const uploaded = [];
  for (const ref of imageRefs(html)) {
    if (/^https:\/\/mmbiz\.qpic\.cn/i.test(ref.src)) continue;
    console.error(`[wechat-draft] Uploading image: ${ref.src}`);
    const resp = await uploadImage(ref.src, accessToken, baseDir);
    const newTag = ref.fullTag.replace(/\ssrc=["'][^"']+["']/, ` src="${resp.url}"`);
    updated = updated.replace(ref.fullTag, newTag);
    uploaded.push({ src: ref.src, media_id: resp.media_id, url: resp.url });
  }
  return { html: updated, uploaded };
}

async function createDraft({ title, author, summary, content, thumbMediaId }, accessToken) {
  const article = {
    article_type: "news",
    title,
    content,
    thumb_media_id: thumbMediaId,
    need_open_comment: 1,
    only_fans_can_comment: 0,
  };
  if (author) article.author = author;
  if (summary) article.digest = summary.length > 120 ? `${summary.slice(0, 117)}...` : summary;

  const res = await fetch(`${DRAFT_URL}?access_token=${encodeURIComponent(accessToken)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ articles: [article] }),
  });
  const data = await res.json();
  if (data.errcode && data.errcode !== 0) throw new Error(`Draft failed ${data.errcode}: ${data.errmsg}`);
  if (!data.media_id) throw new Error(`Unexpected draft response: ${JSON.stringify(data)}`);
  return data;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const htmlPath = resolveInput(args.html);
  const coverPath = resolveInput(args.cover);
  if (!fs.existsSync(htmlPath)) throw new Error(`HTML not found: ${htmlPath}`);
  if (!fs.existsSync(coverPath)) throw new Error(`Cover not found: ${coverPath}`);

  const baseDir = path.dirname(htmlPath);
  const html = fs.readFileSync(htmlPath, "utf8");
  const content = extractBody(html);
  const refs = imageRefs(content);

  if (args.dryRun) {
    console.log(JSON.stringify({
      dryRun: true,
      htmlPath,
      coverPath,
      title: args.title,
      author: args.author || undefined,
      summary: args.summary || undefined,
      contentLength: content.length,
      imageCount: refs.length,
      images: refs.map(r => r.src),
    }, null, 2));
    return;
  }

  const config = loadConfig();
  console.error("[wechat-draft] Fetching access token...");
  const accessToken = await fetchAccessToken(config.appId, config.appSecret);
  console.error("[wechat-draft] Uploading article images...");
  const processed = await uploadImagesInHtml(content, accessToken, baseDir);
  console.error(`[wechat-draft] Uploading cover: ${coverPath}`);
  const cover = await uploadImage(coverPath, accessToken, process.cwd());
  console.error("[wechat-draft] Creating draft...");
  const draft = await createDraft({
    title: args.title,
    author: args.author,
    summary: args.summary,
    content: processed.html,
    thumbMediaId: cover.media_id,
  }, accessToken);

  console.log(JSON.stringify({
    success: true,
    media_id: draft.media_id,
    title: args.title,
    imageCount: processed.uploaded.length,
  }, null, 2));
}

main().catch((error) => {
  console.error(`Error: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
