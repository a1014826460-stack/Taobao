# Crawler API Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the crawler codebase and build a Docker-deployed, multi-user crawler API platform with encrypted profiles, queued jobs, quotas, documentation, and a bilingual React portal.

**Architecture:** Platform service adapters wrap current crawler modules while root modules remain compatibility wrappers. FastAPI owns authorization, PostgreSQL data, encrypted secrets, and job APIs; Redis and Celery execute jobs; the React portal consumes typed REST endpoints.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, Redis, Celery, cryptography, PyJWT, React, Vite, TypeScript, React Router, TanStack Query, i18next, Vitest, Docker Compose.

---

### Task 1: Define packages and shared crawler contracts

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/common/models/crawler.py`
- Create: `src/taobao/{direct,proxy,services}/__init__.py`
- Create: `src/jd/{direct,proxy,services}/__init__.py`
- Test: `tests/test_crawler_models.py`

- [ ] Write failing test:

```python
from src.common.models.crawler import CrawlerExecution, CrawlerName


def test_execution_keeps_profile_ids_separate_from_input():
    execution = CrawlerExecution(
        crawler=CrawlerName.TMALL_SKU_ADJUST,
        input={"item_id": "1007839388129", "sku_id": "6277426546603"},
        credential_profile_id="credential-id",
        proxy_profile_id="proxy-id",
    )
    assert execution.input["sku_id"] == "6277426546603"
    assert execution.credential_profile_id == "credential-id"
```

- [ ] Run `python -m pytest tests/test_crawler_models.py -q`; expect missing-module failure.
- [ ] Add project dependencies (`fastapi`, `sqlalchemy`, `alembic`, `psycopg[binary]`, `celery[redis]`, `cryptography`, `pydantic-settings`, `pyjwt`, `passlib[bcrypt]`, `httpx[socks]`) and pytest config with `pythonpath = ["."]`.
- [ ] Implement `CrawlerName` (`taobao.item`, `taobao.shop`, `tmall.sku-adjust`, `jd.item`, `jd.ware-business`) and Pydantic `CrawlerExecution` with crawler input and optional credential/proxy profile IDs.
- [ ] Run `python -m pytest tests/test_crawler_models.py -q`; expect pass.

### Task 2: Organize crawler implementations while retaining compatibility

**Files:**
- Create: `src/taobao/direct/item.py`, `src/taobao/direct/shop.py`
- Create: `src/jd/direct/item.py`, `src/jd/direct/ware_business.py`
- Create: `src/tmall/direct/shop.py`
- Create: `src/{taobao,tmall,jd}/services/*.py`
- Modify: `src/item_crawler.py`, `src/shop_crawler.py`, `src/jd_item_crawler.py`, `src/jd_ware_business_store.py`, `src/tmall_shop_crawler.py`
- Test: `tests/test_compatibility_imports.py`

- [ ] Write failing test:

```python
from src import item_crawler, jd_item_crawler
from src.jd.direct import item as jd_item
from src.taobao.direct import item as taobao_item
from src.tmall.services import sku_adjust_service


def test_legacy_modules_reexport_relocated_functions():
    assert item_crawler.crawl_items is taobao_item.crawl_items
    assert jd_item_crawler.crawl_jd_items is jd_item.crawl_jd_items
    assert callable(sku_adjust_service.run)
```

- [ ] Run `python -m pytest tests/test_compatibility_imports.py -q`; expect import failure.
- [ ] Move implementations using `git mv`; create legacy wrappers such as:

```python
from src.taobao.direct.item import *  # noqa: F403
from src.taobao.direct.item import main


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] Implement each service adapter as `run(input, cookie, proxy_url) -> dict`; adapters call their existing crawler API, never log or return secrets. Put `api-gw.fan-b.com` implementations only in a platform `proxy/` module.
- [ ] Run `python -m pytest tests/test_compatibility_imports.py tests/test_shop_crawler.py tests/test_jd_item_crawler.py tests/test_jd_ware_business_store.py tests/test_tmall_shop_crawler.py tests/test_taobao_batch.py -q`; expect pass.

### Task 3: Create FastAPI foundation, PostgreSQL models, and migrations

**Files:**
- Create: `backend/app/{main.py,core/config.py,core/security.py,db/base.py,db/session.py}`
- Create: `backend/app/models/{user.py,api_token.py,profile.py,job.py}`
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial_schema.py`
- Create: `backend/tests/{conftest.py,test_health.py}`

- [ ] Write failing health test:

```python
from fastapi.testclient import TestClient
from backend.app.main import create_app


def test_health_returns_service_name():
    response = TestClient(create_app()).get("/api/v1/health")
    assert response.json() == {"status": "ok", "service": "crawler-api"}
```

- [ ] Run `python -m pytest backend/tests/test_health.py -q`; expect import failure.
- [ ] Implement settings for database, Redis, JWT, credential key, admin values, and CORS. Create the SQLAlchemy engine/session and Alembic configuration.
- [ ] Add base tables: `users`, `api_tokens`, `credential_profiles`, `proxy_profiles`, and `crawl_jobs`; include UUID IDs, ownership foreign keys, indexes, timestamps, job status, result JSON, and safe error fields.
- [ ] Implement `/api/v1/health`, then run `python -m pytest backend/tests/test_health.py -q`; expect pass.

### Task 4: Add authentication, API Tokens, and administrator bootstrap

**Files:**
- Create: `backend/app/{schemas/auth.py,services/auth.py,api/deps.py,api/routes/auth.py,api/routes/tokens.py}`
- Modify: `backend/app/main.py`, `backend/alembic/versions/0001_initial_schema.py`
- Test: `backend/tests/test_auth.py`, `backend/tests/test_api_tokens.py`

- [ ] Write failing registration/token tests:

```python
def test_registered_user_receives_five_trials(client):
    response = client.post("/api/v1/auth/register", json={"email": "user@example.com", "password": "CorrectHorse1!"})
    assert response.status_code == 201
    assert response.json()["trial_successes_remaining"] == 5


def test_api_token_is_plaintext_once_and_digest_at_rest(client, auth_headers):
    response = client.post("/api/v1/tokens", json={"name": "local"}, headers=auth_headers)
    assert response.json()["token"].startswith("cap_")
```

- [ ] Run `python -m pytest backend/tests/test_auth.py backend/tests/test_api_tokens.py -q`; expect missing-route failures.
- [ ] Implement bcrypt password hashes; short access JWT and refresh JWT; SHA-256 digested `cap_` API tokens; registration, login, refresh, current-user, token creation/list/revocation routes.
- [ ] Implement first-start admin creation from `ADMIN_EMAIL` and `ADMIN_PASSWORD`, and fail production configuration if required secrets are absent.
- [ ] Run focused auth tests; expect pass.

### Task 5: Encrypt Cookie and proxy profiles at rest

**Files:**
- Create: `backend/app/{core/crypto.py,schemas/profiles.py,services/profiles.py,api/routes/profiles.py}`
- Modify: `backend/app/main.py`, `backend/alembic/versions/0001_initial_schema.py`
- Test: `backend/tests/test_crypto.py`, `backend/tests/test_profiles.py`

- [ ] Write failing tests:

```python
def test_aes_gcm_uses_fresh_nonce(settings):
    first = encrypt_secret("cookie=value", settings.credential_encryption_key)
    second = encrypt_secret("cookie=value", settings.credential_encryption_key)
    assert first != second
    assert decrypt_secret(first, settings.credential_encryption_key) == "cookie=value"


def test_profile_response_redacts_cookie(client, auth_headers):
    created = client.post("/api/v1/profiles/credentials", json={"name": "tmall-main", "platform": "tmall", "cookie": "secret-cookie"}, headers=auth_headers)
    assert "secret-cookie" not in client.get(f"/api/v1/profiles/credentials/{created.json()['id']}", headers=auth_headers).text
```

- [ ] Run `python -m pytest backend/tests/test_crypto.py backend/tests/test_profiles.py -q`; expect failure.
- [ ] Implement AES-256-GCM with a base64 32-byte key, random 12-byte nonce, authenticated ciphertext, strict malformed-key rejection, and no plaintext logging.
- [ ] Implement multi-profile credential CRUD (platform/name/purpose) and proxy CRUD (HTTP/HTTPS/SOCKS5, host/port, optional auth). Enforce ownership and respond with metadata only.
- [ ] Run focused encryption/profile tests; expect pass.

### Task 6: Add rate-limited crawl jobs and Celery execution

**Files:**
- Create: `backend/app/{core/rate_limit.py,schemas/jobs.py,services/crawlers.py,services/jobs.py,workers/celery_app.py,workers/tasks.py,api/routes/crawls.py,api/routes/jobs.py}`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_rate_limit.py`, `backend/tests/test_jobs.py`, `backend/tests/test_worker_quota.py`

- [ ] Write failing trial quota tests:

```python
def test_successful_trial_job_consumes_one_quota(db_session, trial_user, monkeypatch):
    job = create_job(db_session, trial_user, crawler="tmall.sku-adjust", input={"sku_id": "1"})
    monkeypatch.setattr("backend.app.workers.tasks.execute_crawler", lambda *_: {"price": "1"})
    run_job(job.id)
    db_session.refresh(trial_user)
    assert trial_user.trial_successes_remaining == 4


def test_failed_trial_job_preserves_quota(db_session, trial_user, monkeypatch):
    job = create_job(db_session, trial_user, crawler="tmall.sku-adjust", input={"sku_id": "1"})
    monkeypatch.setattr("backend.app.workers.tasks.execute_crawler", lambda *_: (_ for _ in ()).throw(ValueError("bad input")))
    run_job(job.id)
    db_session.refresh(trial_user)
    assert trial_user.trial_successes_remaining == 5
```

- [ ] Run worker tests; expect missing-module failure.
- [ ] Implement Redis sliding-window limits keyed by API Token ID: trial 10/min and formal 60/min. Add `POST /api/v1/crawls/{crawler}` returning 202, `GET /api/v1/jobs/{id}`, and `GET /api/v1/jobs/{id}/result`.
- [ ] In worker, decrypt only selected, owner-checked profiles; construct proxy URLs only in memory; run registry adapters; safely persist results. Use a conditional SQL update to decrement a trial quota only after success; failures never decrement it.
- [ ] Run `python -m pytest backend/tests/test_rate_limit.py backend/tests/test_jobs.py backend/tests/test_worker_quota.py -q`; expect pass.

### Task 7: Add administrator APIs and API reference contracts

**Files:**
- Create: `backend/app/{schemas/admin.py,api/routes/admin.py}`
- Modify: `backend/app/main.py`, `backend/app/schemas/jobs.py`
- Create: `docs/api-reference.md`
- Test: `backend/tests/test_admin.py`

- [ ] Write failing authorization test:

```python
def test_non_admin_cannot_change_other_user_quota(client, auth_headers, other_user):
    response = client.patch(f"/api/v1/admin/users/{other_user.id}", json={"trial_successes_remaining": 100}, headers=auth_headers)
    assert response.status_code == 403
```

- [ ] Run `python -m pytest backend/tests/test_admin.py -q`; expect failure.
- [ ] Add admin user/job listing, user activation/formal/admin/quota updates, and token revocation with an active-admin dependency.
- [ ] Add explicit Pydantic request/response examples, FastAPI route summaries, status/error response declarations, and complete API guide covering JWT, API Token, profiles, five crawler requests, job polling, limits, and errors in Chinese and English.
- [ ] Run admin test and `python -c "from backend.app.main import create_app; assert '/api/v1/crawls/{crawler}' in create_app().openapi()['paths']"`; expect both pass.

### Task 8: Build the bilingual Apple-inspired React portal

**Files:**
- Create: `frontend/{package.json,vite.config.ts,tsconfig.json,index.html}`
- Create: `frontend/src/{main.tsx,App.tsx,i18n.ts,api/client.ts,api/types.ts,styles/theme.css}`
- Create: `frontend/src/locales/{zh-CN.json,en-US.json}`
- Create: `frontend/src/components/{AppShell.tsx,ApiExample.tsx,SecretProfileForm.tsx}`
- Create: `frontend/src/pages/{LandingPage.tsx,LoginPage.tsx,RegisterPage.tsx,DashboardPage.tsx,PlaygroundPage.tsx,ProfilesPage.tsx,DocsPage.tsx,AdminPage.tsx}`
- Test: `frontend/src/components/SecretProfileForm.test.tsx`, `frontend/src/i18n.test.ts`

- [ ] Write failing safety/i18n tests:

```tsx
it("clears the cookie input after saving", async () => {
  render(<SecretProfileForm onSave={vi.fn().mockResolvedValue(undefined)} />)
  await userEvent.type(screen.getByLabelText("Cookie"), "secret=value")
  await userEvent.click(screen.getByRole("button", { name: /save/i }))
  expect(screen.getByLabelText("Cookie")).toHaveValue("")
})
```

- [ ] Run `npm --prefix frontend test -- --run`; expect scaffold failure.
- [ ] Scaffold React/Vite/TypeScript with React Router, TanStack Query, i18next, Vitest, and Testing Library. Implement Chinese default with English switch.
- [ ] Implement light/dark Apple-style design: glass cards, reserved gradients, large radii, high contrast typography, responsive console layout, and `prefers-reduced-motion` support.
- [ ] Build landing, auth, dashboard, crawler playground with job polling, safe credential/proxy manager, API docs with examples, and admin pages. Never display persisted Cookies or proxy passwords.
- [ ] Run `npm --prefix frontend test -- --run` and `npm --prefix frontend run build`; expect pass/build.

### Task 9: Containerize, document, and verify deployment

**Files:**
- Create: `docker-compose.yml`, `.env.example`, `README.md`
- Create: `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`
- Test: `backend/tests/test_compose_configuration.py`

- [ ] Write failing test that asserts Compose services include `api`, `worker`, `postgres`, `redis`, and `frontend`.
- [ ] Run `python -m pytest backend/tests/test_compose_configuration.py -q`; expect missing-file failure.
- [ ] Build Compose services: PostgreSQL 16 and Redis 7 with volumes; API runs migrations then Uvicorn; Worker uses the API image and Celery; Frontend Nginx serves Vite output and proxies `/api/` to FastAPI.
- [ ] Create `.env.example` with placeholders for PostgreSQL, Redis, JWT secret, base64 credential key, and bootstrap admin environment variables. Document secure secret creation, startup, migration, docs URLs, crawler API usage, and full test commands.
- [ ] Run `python -m pytest backend/tests/test_compose_configuration.py -q`, `docker compose config`, `python -m pytest -q`, `npm --prefix frontend test -- --run`, and `npm --prefix frontend run build`; expect all pass.

### Task 10: Commit in reviewable slices

**Files:**
- Modify only files from Tasks 1-9 as needed for verification.

- [ ] Run `git ls-files | Select-String -Pattern '(^data/|\.env$|\.sqlite$|\.xlsx$)'` and `git diff --check`; expect no crawl data, secrets, or whitespace errors.
- [ ] Commit crawler package work with `refactor: organize crawler services by platform`.
- [ ] Commit FastAPI and worker work with `feat: add authenticated crawler API`.
- [ ] Commit portal work with `feat: add crawler API portal`.
- [ ] Commit Compose and documentation with `docs: add crawler platform deployment guide`.
