# Crawler API Platform Design

## Goal

Build a multi-user crawler API platform that exposes the existing Taobao,
Tmall, and JD crawlers through authenticated REST APIs, an API documentation
portal, and an Apple-inspired bilingual web console.

## Scope

- Reorganize crawler source by platform and responsibility without breaking
  existing imports or command-line entry points.
- Provide user registration, login, JWT sessions, API tokens, trial quotas,
  user credentials, proxy profiles, jobs, and administrator controls.
- Run crawler jobs asynchronously with Celery and Redis.
- Store user and job data in PostgreSQL.
- Encrypt persisted Cookie and proxy secrets with AES-256-GCM.
- Deliver a React + Vite portal in Simplified Chinese and English.
- Publish OpenAPI and human-readable API reference documentation.
- Deploy all services using Docker Compose.

## Non-Goals

- Billing, payment, subscription purchase, and email verification are not in
  the first release.
- Browser automation is not a service dependency for ordinary API requests.
- Plaintext Cookies and proxy credentials are never returned after creation.

## Architecture

```text
React + Vite portal
        |
        v
FastAPI API -------- PostgreSQL
   |  |                  |
   |  +--- Redis --------+
   |          |
   v          v
Celery Worker -> crawler service adapters -> target site or configured proxy
```

FastAPI authenticates portal sessions and API Tokens, validates requests,
applies per-token limits, persists jobs, and queues crawler work. Celery
workers resolve the referenced encrypted credential and proxy profile only at
execution time, invoke the appropriate crawler service, and persist a
sanitized result. The portal polls job status and renders response data.

## Source Layout

```text
src/
  common/
    credentials/       # Encrypt/decrypt interfaces and secret redaction.
    http/              # Request and proxy transport helpers.
    models/            # Shared crawler request/result types.
  taobao/
    direct/
    proxy/
    services/
    compat/            # Compatibility wrappers for existing script imports.
  tmall/
    direct/
    proxy/
    services/
  jd/
    direct/
    proxy/
    services/
  tools/
backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
    workers/
frontend/
```

`direct` modules call target-site APIs directly. `proxy` modules contain
proxy-routed variants or transport adapters, including `api-gw.fan-b.com`.
`services` expose stable crawler-specific operations to the API layer.
Existing root-level crawler module paths remain small compatibility wrappers
that re-export the relocated public functions, preserving current tests and
commands during migration.

## Identity and Access

- Users self-register with email and password and can log in immediately.
- The login endpoint returns a short-lived JWT access token and refresh token.
- Users create named long-lived API Tokens. Only a one-time plaintext value is
  shown at creation; the database stores a SHA-256 token digest.
- New accounts have a trial allowance of five successful crawler jobs.
- Failed, cancelled, invalid, and rate-limited requests do not consume trial
  quota. The worker atomically consumes quota only after a successful result
  has been persisted.
- Administrators can view users and jobs, promote users, set a custom quota,
  disable users, and revoke API Tokens.
- First startup creates the administrator from `ADMIN_EMAIL` and
  `ADMIN_PASSWORD`; it fails fast when either value is absent in production.

## Credential and Proxy Profiles

Each user can create multiple named profiles per platform and purpose:

- Credential profile: platform (`taobao`, `tmall`, `jd`), name, optional
  purpose label, encrypted Cookie value, and timestamps.
- Proxy profile: name, protocol (`http`, `https`, `socks5`), host, port,
  optional encrypted username/password, and timestamps.

Secrets use AES-256-GCM with a 32-byte `CREDENTIAL_ENCRYPTION_KEY` supplied as
a base64 environment variable. Each encrypted value has a unique random nonce
and authenticated ciphertext. Profile list/detail endpoints expose metadata
only. Worker logs and job payloads use redacted representations.

## API and Job Model

All crawler operations use a consistent asynchronous contract:

1. `POST /api/v1/crawls/{crawler}` accepts target parameters and optional
   `credential_profile_id` and `proxy_profile_id`.
2. The API creates a `queued` job and returns `202 Accepted` with its ID.
3. `GET /api/v1/jobs/{id}` returns `queued`, `running`, `succeeded`, `failed`,
   or `cancelled` status with safe error metadata.
4. `GET /api/v1/jobs/{id}/result` returns a normalized crawler result after
   completion.

Initial crawler names are:

- `taobao.item`
- `taobao.shop`
- `tmall.sku-adjust`
- `jd.item`
- `jd.ware-business`

Each endpoint publishes explicit Pydantic request/response schemas. The
documentation includes `curl`, JavaScript, and Python examples, plus success
and error JSON samples.

## Limits and Reliability

- Trial API Tokens: 10 requests per minute.
- Formal-user API Tokens: 60 requests per minute.
- Redis uses a sliding-window counter keyed by API Token ID.
- Workers use idempotent task IDs linked to database job IDs and retry only
  transient network failures with bounded exponential backoff.
- A job has a configurable maximum runtime and records a terminal error code
  rather than exposing stack traces to standard users.

## Web Portal

The React application uses TypeScript, Vite, React Router, TanStack Query,
and i18next. It supports light and dark themes and Simplified Chinese/English.

Visual direction: high-contrast typography, restrained gradients, large
rounded cards, frosted surfaces, fine borders, generous whitespace, smooth
but reduced-motion-aware transitions, and a console-oriented documentation
layout. It contains:

- Landing page and API overview.
- Registration and login.
- Dashboard with quota, API Token, and recent-job summaries.
- Crawler playground with schema-driven forms and live job status.
- Credential and proxy profile manager that never redisplays secrets.
- API documentation with endpoint explorer and examples.
- Administrator pages for users, quota, token revocation, and jobs.

## Documentation

FastAPI serves OpenAPI JSON at `/openapi.json`, Swagger UI at `/docs`, and
ReDoc at `/redoc`. The portal presents a curated API reference that explains
authentication, rate limits, crawler inputs, job polling, credential profiles,
proxy profiles, error codes, request examples, and response examples.

## Deployment

`docker-compose.yml` runs `frontend`, `api`, `worker`, `postgres`, and
`redis`. The API container runs Alembic migrations before serving. Docker
Compose environment files provide non-secret defaults; production secrets are
injected by the deployment environment. PostgreSQL and Redis volumes persist
state across restarts.

## Testing

- Unit tests: encryption, token hashing, trial accounting, schemas, rate-limit
  decisions, and crawler service adapters with mocked transport.
- API tests: registration, authorization, profile redaction, job creation,
  permission boundaries, and admin controls.
- Worker tests: success consumes one trial; failures do not consume quota.
- Frontend tests: navigation guards, language switching, safe secret forms,
  and job status rendering.
- Compose smoke test: API health endpoint, migration, worker connectivity, and
  a deterministic mocked crawler task.

## Acceptance Criteria

- Existing crawler imports and CLI behavior remain compatible after source
  reorganization.
- A registered user can create a Cookie and proxy profile, launch a permitted
  crawler job, inspect its result, and see quota decrease only after success.
- A user cannot read another user's profiles or jobs.
- A credential value is encrypted at rest and never returned by API or UI.
- Trial and formal-user rate limits are enforced by API Token.
- Administrators can manage user status, quota, tokens, and jobs.
- The API portal documents every public endpoint with input and response
  examples in both Chinese and English.
