#!/usr/bin/env node

import { createServer } from "node:http";
import { readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { spawn } from "node:child_process";

const { chromium } = await import("playwright");

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const part = argv[index];
    if (!part.startsWith("--")) continue;
    const key = part.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      args[key] = "true";
      continue;
    }
    args[key] = next;
    index += 1;
  }
  return args;
}

function runCommand(command, commandArgs, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, commandArgs, {
      cwd: options.cwd,
      stdio: ["ignore", "pipe", "pipe"],
      env: options.env ?? process.env,
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("exit", (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
        return;
      }
      reject(new Error(`${command} ${commandArgs.join(" ")} failed with code ${code}\n${stderr || stdout}`));
    });
  });
}

function contentTypeFor(filePath) {
  if (filePath.endsWith(".html")) return "text/html; charset=utf-8";
  if (filePath.endsWith(".js")) return "text/javascript; charset=utf-8";
  if (filePath.endsWith(".css")) return "text/css; charset=utf-8";
  if (filePath.endsWith(".json")) return "application/json; charset=utf-8";
  if (filePath.endsWith(".svg")) return "image/svg+xml";
  if (filePath.endsWith(".png")) return "image/png";
  if (filePath.endsWith(".woff2")) return "font/woff2";
  return "application/octet-stream";
}

async function createStaticServer(rootDir, port) {
  const server = createServer(async (request, response) => {
    try {
      const requestPath = request.url === "/" ? "/index.html" : request.url || "/index.html";
      const normalized = requestPath.split("?")[0];
      const filePath = path.join(rootDir, normalized);
      const fileInfo = await stat(filePath);
      if (fileInfo.isDirectory()) {
        const indexPath = path.join(filePath, "index.html");
        const buffer = await readFile(indexPath);
        response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        response.end(buffer);
        return;
      }
      const buffer = await readFile(filePath);
      response.writeHead(200, { "Content-Type": contentTypeFor(filePath) });
      response.end(buffer);
    } catch (_error) {
      response.writeHead(404);
      response.end("Not found");
    }
  });
  await new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
  return server;
}

async function ensureAppBuilt(appDir) {
  await runCommand("npm", ["ci"], { cwd: appDir });
  await runCommand("npm", ["run", "build"], { cwd: appDir });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const manifestPath = args.manifest;
  const outputPath = args.output;
  const port = Number(args.port || 4173);

  if (!manifestPath || !outputPath) {
    throw new Error("Usage: export_png.mjs --manifest <path> --output <path> [--port <port>]");
  }

  const manifest = JSON.parse(await readFile(manifestPath, "utf-8"));
  const appDir = manifest.appDir;
  const entryHtml = manifest.entryHtml || null;
  const distDir = path.join(appDir, "dist");

  if (!entryHtml) {
    await ensureAppBuilt(appDir);
  }
  const serverRoot = entryHtml ? appDir : distDir;
  const server = await createStaticServer(serverRoot, port);

  try {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({
      viewport: { width: 1000, height: 2200 },
      deviceScaleFactor: 2.5,
    });
    await page.goto(`http://127.0.0.1:${port}`, { waitUntil: "networkidle" });
    await page.addStyleTag({
      content: `
        .no-capture { display: none !important; }
        body { margin: 0; background: #cbd5e1 !important; }
      `,
    });
    await page.evaluate(async () => {
      if (document.fonts && "ready" in document.fonts) {
        await document.fonts.ready;
      }
    });

    await page.evaluate(async () => {
      const step = Math.max(Math.floor(window.innerHeight * 0.8), 400);
      const maxY = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
      for (let y = 0; y < maxY; y += step) {
        window.scrollTo(0, y);
        await new Promise((resolve) => setTimeout(resolve, 80));
      }
      window.scrollTo(0, 0);
      await new Promise((resolve) => setTimeout(resolve, 120));
    });

    const dataUrl = await page.evaluate(async () => {
      const exporter = window.__MARKET_REPORT_EXPORT__;
      if (typeof exporter === "function") {
        return exporter();
      }
      const target = document.documentElement;
      if (!target) {
        throw new Error("No document root available for screenshot export");
      }
      return null;
    });
    if (typeof dataUrl === "string" && dataUrl.startsWith("data:image/png;base64,")) {
      const base64 = dataUrl.replace("data:image/png;base64,", "");
      await writeFile(outputPath, Buffer.from(base64, "base64"));
      await browser.close();
      return;
    }

    await page.screenshot({ path: outputPath, fullPage: true, type: "png" });
    await browser.close();
  } finally {
    await new Promise((resolve, reject) => {
      server.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve();
      });
    });
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
