# Market Report Deployment Design

**Date:** 2026-03-12

## Goal

Deploy the market report web app to `market-report.chenchen.city` on `flareserver` without exposing the Gemini API key to the frontend.

## Current State

- The project is a Vite + React application.
- Gemini is called directly from the browser in `src/App.tsx`.
- `vite.config.ts` injects `GEMINI_API_KEY` into the frontend bundle.
- The project is not yet initialized as a git repository in the project directory.

## Recommended Architecture

Use a split runtime on one server:

- Frontend: Vite build output served as static files by Nginx
- Backend: Python FastAPI service running under `systemd`
- Reverse proxy: Nginx routes `/api/*` to FastAPI and `/` to static assets
- Secrets: Gemini key stored only on the server in an environment file read by `systemd`

## Why This Approach

- Keeps `GEMINI_API_KEY` out of browser code and out of git
- Aligns with the workspace rule that backend defaults to Python
- Keeps the existing React UI with minimal product change
- Makes deployment and rollback simple on a single server

## Request Flow

1. User uploads `.txt`, `.md`, `.docx`, or `.json` from the browser.
2. Frontend reads local files when needed.
3. For `.json`, frontend validates and renders locally.
4. For text and `.docx`, frontend sends extracted text to `POST /api/parse-report`.
5. FastAPI calls Gemini with the server-side key and returns structured JSON.
6. Frontend renders the report and allows PNG export.

## Backend Design

- Framework: FastAPI
- Runtime endpoint:
  - `GET /api/health`
  - `POST /api/parse-report`
- Gemini integration:
  - Read `GEMINI_API_KEY` from environment
  - Reuse the existing response schema semantics
- Validation:
  - Reject empty request bodies
  - Require `sections` in the model response
  - Return clear 4xx/5xx errors to the frontend

## Frontend Design

- Remove `@google/genai` browser usage
- Remove Vite env injection for `GEMINI_API_KEY`
- Replace direct Gemini call with `fetch('/api/parse-report')`
- Keep current upload flow and PNG export behavior
- Keep `.json` uploads local-only

## Deployment Design

- Build frontend with `npm run build`
- Create Python virtualenv for backend
- Run backend with `systemd`
- Serve `dist/` from Nginx
- Proxy `/api/` to `127.0.0.1:<backend-port>`
- Add DNS A record for `market-report.chenchen.city` to `43.153.52.15`

## Security Notes

- Never commit `.env`, service secrets, or server-only config with keys
- Keep API key only on the server
- Do not embed key in Vite env or `window` globals
- Add backend-side request size and empty input validation

## Testing Strategy

- Add backend tests for:
  - health endpoint
  - parse endpoint validation
- Add frontend tests for:
  - API helper success path
  - API helper error path
- Run TypeScript check
- Run Python tests
- Run production build

## Rollout Plan

1. Initialize git repo and baseline ignores
2. Add design and implementation docs
3. Write tests first
4. Implement backend
5. Migrate frontend to backend API
6. Add deployment files and docs
7. Verify locally
8. Commit and push to GitHub
9. Deploy to `flareserver`
10. Configure DNS and verify domain
