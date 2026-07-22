# Crawler API Platform

Multi-user APIs for Taobao, Tmall, and JD crawler services.

## Start

1. Copy `.env.example` to `.env` and replace every secret.
2. Run `docker compose up --build`.
3. Open the portal at `http://localhost:8080`, Swagger at `http://localhost:8000/docs`, and ReDoc at `http://localhost:8000/redoc`.

## API Flow

Register with `POST /api/v1/auth/register`, log in with `POST /api/v1/auth/login`,
then send the JWT as `Authorization: Bearer <token>`. Create named Cookie and
proxy profiles before submitting a crawler job. Cookie and proxy authentication
values are AES-256-GCM encrypted in storage and never returned by profile APIs.

New accounts have five successful-job trials. Trial requests are limited to
10/min; formal users are limited to 60/min. Failed jobs do not consume quota.

## Layout

- `src/taobao`, `src/tmall`, `src/jd`: platform crawler modules.
- `direct`: target-site requests; `proxy`: intermediary-routed integrations.
- `services`: stable adapters used by the API worker.
- `backend`: FastAPI, profiles, jobs, and Celery task infrastructure.
- `frontend`: React + Vite bilingual API portal.

Run Python checks with `python -m pytest -q`; build the portal with
`npm --prefix frontend run build`.
