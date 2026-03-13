# Market Report Secure Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move Gemini parsing to a Python backend, deploy the app to `market-report.chenchen.city`, and keep secrets off the frontend.

**Architecture:** The React frontend remains a static Vite app. A new FastAPI service handles Gemini parsing and runs behind Nginx on `flareserver`, with secrets supplied through a server-only environment file.

**Tech Stack:** React 19, TypeScript, Vite, FastAPI, pytest, Nginx, systemd

---

### Task 1: Create project planning docs and repository baseline

**Files:**
- Create: `docs/plans/2026-03-12-market-report-deployment-design.md`
- Create: `docs/plans/2026-03-12-market-report-deployment.md`
- Modify: `.gitignore`

**Step 1: Ensure planning docs exist**

Check: `ls docs/plans`
Expected: both design and implementation plan files are present

**Step 2: Expand ignore rules for Python and deployment artifacts**

Add ignores for:
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`

**Step 3: Verify ignore file is safe**

Run: `sed -n '1,200p' .gitignore`
Expected: no secrets added, `.env*` remains ignored, `.env.example` remains tracked

**Step 4: Commit planning baseline**

```bash
git add .gitignore docs/plans
git commit -m "docs: add deployment design and implementation plan"
```

### Task 2: Add backend tests before implementation

**Files:**
- Create: `backend/tests/test_main.py`
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`

**Step 1: Write failing health endpoint test**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health_endpoint_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_main.py -q`
Expected: FAIL because `app.main` does not exist yet

**Step 3: Write failing parse validation test**

```python
def test_parse_report_rejects_empty_text():
    response = client.post("/api/parse-report", json={"text": ""})
    assert response.status_code == 422
```

**Step 4: Run test to verify it fails for the missing app**

Run: `pytest backend/tests/test_main.py -q`
Expected: FAIL because the backend is not implemented yet

**Step 5: Commit test scaffolding**

```bash
git add backend/tests/test_main.py backend/requirements.txt backend/requirements-dev.txt
git commit -m "test: add backend API expectations"
```

### Task 3: Add frontend API tests before migration

**Files:**
- Create: `src/lib/api.ts`
- Create: `src/lib/api.test.ts`
- Modify: `package.json`

**Step 1: Write failing API helper test**

```typescript
import { describe, expect, it, vi } from 'vitest';
import { parseReportText } from './api';

describe('parseReportText', () => {
  it('posts text to the backend and returns parsed report data', async () => {
    const payload = { sections: [] };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    }));

    await expect(parseReportText('demo')).resolves.toEqual(payload);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- src/lib/api.test.ts`
Expected: FAIL because the helper and test runner are not fully configured yet

**Step 3: Add error-path test**

```typescript
it('throws a readable error when the backend returns an error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: false,
    json: async () => ({ detail: 'bad request' }),
  }));

  await expect(parseReportText('demo')).rejects.toThrow('bad request');
});
```

**Step 4: Run test again to confirm red state**

Run: `npm test -- src/lib/api.test.ts`
Expected: FAIL with missing implementation

**Step 5: Commit frontend test expectations**

```bash
git add package.json src/lib/api.test.ts
git commit -m "test: add frontend API client expectations"
```

### Task 4: Implement the FastAPI backend

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/models.py`
- Create: `backend/app/gemini_client.py`
- Create: `backend/app/main.py`
- Modify: `backend/tests/test_main.py`

**Step 1: Implement minimal health endpoint**

Run: `pytest backend/tests/test_main.py::test_health_endpoint_returns_ok -q`
Expected: PASS

**Step 2: Implement request model and empty-text validation**

Run: `pytest backend/tests/test_main.py::test_parse_report_rejects_empty_text -q`
Expected: PASS

**Step 3: Implement Gemini client wrapper**

Behavior:
- read `GEMINI_API_KEY`
- submit prompt and schema
- return parsed JSON

**Step 4: Implement parse endpoint using the wrapper**

Run: `pytest backend/tests/test_main.py -q`
Expected: all backend tests PASS

**Step 5: Commit backend implementation**

```bash
git add backend
git commit -m "feat: add secure backend parsing API"
```

### Task 5: Migrate the frontend to the backend API

**Files:**
- Modify: `src/App.tsx`
- Create: `src/lib/api.ts`
- Modify: `vite.config.ts`
- Modify: `package.json`

**Step 1: Implement the API helper**

Run: `npm test -- src/lib/api.test.ts`
Expected: PASS

**Step 2: Replace browser Gemini calls with backend fetch calls**

Behavior:
- remove `@google/genai`
- remove `process.env.GEMINI_API_KEY`
- call `parseReportText`

**Step 3: Remove secret injection from Vite config**

Run: `npm run lint`
Expected: PASS

**Step 4: Run frontend tests and type-check**

Run: `npm test -- src/lib/api.test.ts && npm run lint`
Expected: PASS

**Step 5: Commit frontend migration**

```bash
git add src/App.tsx src/lib/api.ts src/lib/api.test.ts vite.config.ts package.json package-lock.json
git commit -m "feat: move Gemini usage behind backend API"
```

### Task 6: Add production deployment assets

**Files:**
- Create: `deploy/systemd/market-report.service`
- Create: `deploy/nginx/market-report.conf`
- Create: `deploy/scripts/deploy.sh`
- Modify: `README.md`
- Modify: `.env.example`

**Step 1: Add backend and deployment instructions**

Include:
- local backend startup
- frontend build
- server environment variables

**Step 2: Add systemd unit**

Behavior:
- working directory points to app checkout
- reads environment file
- starts uvicorn

**Step 3: Add Nginx config**

Behavior:
- serves frontend static files
- proxies `/api/`

**Step 4: Add deployment script**

Behavior:
- install backend deps
- build frontend
- sync static files
- restart systemd

**Step 5: Commit deployment assets**

```bash
git add deploy README.md .env.example
git commit -m "chore: add production deployment assets"
```

### Task 7: Verify and release

**Files:**
- Modify as needed after verification

**Step 1: Run full local verification**

Run:
- `pytest backend/tests -q`
- `npm test -- src/lib/api.test.ts`
- `npm run lint`
- `npm run build`

Expected: all commands succeed

**Step 2: Initialize git repo if needed and create main branch**

Run:

```bash
git init
git branch -M main
```

**Step 3: Create GitHub repository and push**

Run:

```bash
gh repo create market-report --private --source=. --remote=origin --push
```

Adjust repo visibility or name if the default is already taken.

**Step 4: Deploy to `flareserver`**

Run:
- copy repo or clone on server
- install Python and Node runtime dependencies if missing
- place secret env file on server
- enable and restart `market-report.service`
- enable Nginx site and reload

**Step 5: Configure DNS**

Run `tccli` to create the A record:
- name: `market-report`
- type: `A`
- value: `43.153.52.15`

**Step 6: Verify production**

Run:
- `curl http://127.0.0.1:<backend-port>/api/health` on server
- `curl -I http://market-report.chenchen.city`

Expected: health returns `200`, site responds successfully
