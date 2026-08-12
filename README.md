# Crawler API Platform

Multi-user APIs for Taobao, Tmall, and JD crawler services.

## Start

1. Copy `.env.example` to `.env` and replace every secret. Generate a real
   `CREDENTIAL_ENCRYPTION_KEY` with the command in that file; it must be a
   URL-safe base64-encoded 32-byte key. `FANB_API_KEY` and `FANB_API_SECRET`
   are required only for the Taobao/JD data-gateway APIs.
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

## Taobao Keyword Search

Set `FANB_API_KEY` and `FANB_API_SECRET` in `.env` (or the process
environment), then crawl a keyword with the Fan-B `item_search` gateway:

```powershell
python -m src.taobao.direct.search `
  --q '润滑液' `
  --max-pages 10 `
  --workers 4
```

The crawler requests pages 1 through `--max-pages` concurrently, defaults to
`--sort _sale` (sales order), and saves raw response pages plus normalized
search items to `data/taobao_search.sqlite3`. Re-running skips successful
pages for the same query and filters; use `--reset` to fetch them again.
Use `python -m src.taobao.direct.search --help` for price and gateway filter
arguments.

Upload all stored main images to the Guonei collection endpoint with:

```powershell
python -m src.tools.upload_taobao_search_to_guonei
```

The uploader sends JSON batches containing the documented `淘宝` platform,
`首图` image type, the stored keyword/page/link/title/main image/raw search
item, and maps only `_sale` to `销量`; all other sorts map to `综合`.

## Taobao Search Item Details

After saving comprehensive-sort (`sort` empty) search pages, crawl the detail data
for unique商品 IDs through Fan-B `item_get`:

```powershell
python -m src.taobao.direct.item `
  --from-search-db data/taobao_search.sqlite3 `
  --search-sort '' `
  --per-keyword-limit 200 `
  --item-api item_get `
  --workers 8 `
  --db data/taobao_item_get.sqlite3
```

The command deduplicates商品 ID within each keyword, caps each keyword at
`--per-keyword-limit` IDs, runs concurrent requests, and stores raw detail JSON,
normalized fields, success/error state, and the originating keyword/page in
SQLite. Re-running skips successful商品 IDs unless `--reset` is supplied.

## JD Keyword Search

Set `FANB_API_KEY` and `FANB_API_SECRET` in `.env` (or `KEY` / `SECRET`), then crawl JD search pages through Fan-B `jd/item_search`:

```powershell
python -m src.jd.direct.search `
  --q '手机' `
  --sort _sale `
  --max-pages 10 `
  --workers 4
```

<<Supported JD `sort` values are `bid`, `_bid`, `_sale`, `_review`, and `_new`.
`bid` means total price, `sale` means sales, `review` means review count, and `new` means new products; adding the `_` prefix means descending order. Results are stored in `data/jd_search.sqlite3` with raw pages, normalized items, and resumable page state.

## Taobao/Tmall Browser Capture Crawler

The browser crawler uses one isolated Camoufox context per account and stores
captured JSON in a separate SQLite database (default:
`data/taobao_browser_crawler.db`). It supports both repeatable command-line
keywords and tasks already queued in the database. Browsers are visible by
default; add `--headless` for unattended runs.

### Accounts and cookies

Pass one account with `--cookie-file`, or a directory containing one cookie
file per account with `--cookie-dir`:

```text
cookies/accounts/
  alice.txt
  bob.json
```

Cookie files may be semicolon, Netscape, or JSON (`[...]` or
`{"cookies": [...]}`) format. File stems become stable account IDs. Cookie
values are injected only into that account's browser context and are redacted
before network metadata or raw payloads are persisted; do not commit cookie
files.

### CLI examples

Capture up to three pages per keyword for both Taobao and Tmall, then process
the discovered detail tasks:

```powershell
$env:PYTHONPATH = "src"
python -m taobao.browser.cli `
  --keyword '手机' --keyword '耳机' `
  --cookie-dir cookies/accounts `
  --db data/taobao_browser_crawler.db
```

Use a single test account, capture search pages only, or run queued tasks:

```powershell
python -m taobao.browser.cli --keyword '手机' --cookie-file cookies.txt --search-only
python -m taobao.browser.cli --from-tasks --cookie-dir cookies/accounts --headless
```

`--pages` is limited to 1–3 (default 3), `--min-delay`/`--max-delay` default
to 10–30 seconds, and `--retry-limit` bounds transient retries. Every page is
allowed to load naturally and receives bounded stay/scroll/mouse actions.

### Database and resume behavior

The browser database contains `crawl_runs`, `accounts`, `crawl_tasks`,
`network_records`, `search_products`, `product_details`, `product_comments`,
and `seller_infos`. It preserves redacted raw JSON for later parsing and uses
unique keys for keyword/page and platform/item records, so reruns are
idempotent. A crashed run requeues tasks left in `running`; successful tasks
are skipped.

If a login expiry, challenge, rate limit, or forbidden response is detected,
only the affected account is marked `paused`, its in-flight task is requeued,
and other accounts continue. Resume after resolving the account issue by
running `--from-tasks` with that account available again (or by clearing its
pause state in the database under operator control). The CLI returns non-zero
when work remains failed or paused.

Automated tests use local response/page fixtures and never contact Taobao.
Before a real-site run, manually verify the supplied account, requested
keywords, pacing range, and risk handling in a visible browser; perform a
small bounded smoke run first. Real-site verification is intentionally not
part of the test suite.`r`nSupported JD `sort` values are `bid`, `_bid`, `_sale`, `_review`, `_new`, and an empty string for comprehensive order.
`bid` means total price, `sale` means sales, `review` means review count, and `new` means new products; adding the `_` prefix means descending order. When `jd/item_search` fails after its configured retries, the crawler automatically retries that page through `jd/item_search_pro` with the same filters and sort value. Results are stored in `data/jd_search.sqlite3` with raw pages, normalized items, and resumable page state.

