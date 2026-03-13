# 全市场研报分析 - 周更

这个项目现在采用前后端分离的单机部署方式：

- 前端：Vite + React，负责上传文件、展示结果、导出图片
- 后端：FastAPI，负责调用 Gemini 并返回结构化 JSON
- 生产环境：Nginx 反代 `market-report.chenchen.city`

## 本地开发

### 1. 安装前端依赖

```bash
npm install
```

### 2. 安装后端依赖

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
```

### 3. 配置环境变量

复制 [.env.example](.env.example) 到服务器环境文件或本地 shell 环境中，并设置：

```bash
export GEMINI_API_KEY="your_server_only_gemini_key"
export GEMINI_MODEL="gemini-2.0-flash"
```

### 4. 启动后端

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

### 5. 启动前端

```bash
npm run dev
```

开发环境下，Vite 会将 `/api/*` 代理到 `http://127.0.0.1:8000`。

## 测试

```bash
.venv/bin/python -m pytest backend/tests -q
npx vitest run src/lib/api.test.ts
npm run lint
npm run build
```

## 生产部署

仓库包含以下部署文件：

- `deploy/systemd/market-report.service`
- `deploy/nginx/market-report.conf`
- `deploy/scripts/deploy.sh`

在 `flareserver` 上：

1. 准备 Node.js、Python 3、Nginx
2. 将项目放到 `/opt/market-report`
3. 将服务端环境变量写入 `/etc/market-report.env`
4. 安装 `systemd` 和 Nginx 配置
5. 执行部署脚本
6. 用 `tccli` 为 `market-report.chenchen.city` 添加 A 记录到 `43.153.52.15`
