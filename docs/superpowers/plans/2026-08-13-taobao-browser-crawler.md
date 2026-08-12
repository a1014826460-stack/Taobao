# 淘宝浏览器抓包爬虫 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a resumable Taobao/Tmall browser crawler using isolated Camoufox instances per account, capturing search/detail JSON into a dedicated SQLite database with humanized pacing and account-level risk pausing.

**Architecture:** A single-process scheduler assigns keyword and detail tasks to an account browser pool. Each account owns an isolated Camoufox browser/context and cookie jar. A crawler captures XHR/fetch/JSON responses, redacts secrets, classifies payloads, normalizes business records, and writes idempotently to SQLite. CLI input and database task input share the same scheduler.

**Tech Stack:** Python 3.11+, Camoufox/Playwright, SQLite (`sqlite3`), `argparse`, `pytest`/`unittest`, installed `camoufox-reverse-mcp` for reconnaissance and protocol parity.

## Global Constraints

- Use a separate database at `data/taobao_browser_crawler.db`; do not alter existing API crawler schemas.
- Support Taobao and Tmall, with at most 3 search pages per keyword by default.
- Detail tasks cover every unique item discovered by successful search pages.
- Save first-screen and naturally loaded JSON; do not add unbounded comment pagination.
- One isolated browser/context per account; never share cookies or storage between accounts.
- Default visible browser; `--headless` is opt-in.
- Page actions use configurable random delays, default 10–30 seconds, plus stay/scroll/mouse behavior.
- Pause only the affected account on login/risk/challenge conditions; requeue its task and continue other accounts.
- Redact Cookie, Set-Cookie, Authorization, token/sign query values before persistence/logging.
- Use bounded retries and resumable state; never re-fetch successful tasks unless an explicit reset option is added.
- Do not touch unrelated existing worktree modifications.

---

## File Map

**Create:**
- `src/taobao/browser/__init__.py` — package exports.
- `src/taobao/browser/accounts.py` — cookie format parsing, account discovery and state model.
- `src/taobao/browser/repository.py` — SQLite schema, migrations, task/run/account persistence and idempotent upserts.
- `src/taobao/browser/network_capture.py` — response metadata, redaction, JSON detection/classification and capture records.
- `src/taobao/browser/human_behavior.py` — bounded random delay, scrolling and mouse trajectory helpers.
- `src/taobao/browser/risk_control.py` — page/response risk classification and account pause decisions.
- `src/taobao/browser/browser_pool.py` — per-account Camoufox browser/context lifecycle and cookie injection.
- `src/taobao/browser/crawler.py` — search/detail workflow and task scheduling integration.
- `src/taobao/browser/cli.py` — CLI parsing and execution entry point.
- `tests/test_taobao_browser_accounts.py`
- `tests/test_taobao_browser_repository.py`
- `tests/test_taobao_browser_network.py`
- `tests/test_taobao_browser_behavior.py`
- `tests/test_taobao_browser_risk.py`
- `tests/test_taobao_browser_crawler.py`
- `tests/test_taobao_browser_cli.py`
- `tests/fixtures/taobao_browser/` — local HTML/HTTP fixture payloads.

**Modify:**
- `pyproject.toml` only if a missing runtime/test dependency is proven necessary.

---

### Task 1: Add package skeleton and account/Cookie parsing

**Files:** Create `src/taobao/browser/__init__.py`, `src/taobao/browser/accounts.py`, `tests/test_taobao_browser_accounts.py`.

**Interfaces:**
- `CookieRecord` dataclass with `name`, `value`, `domain`, `path`, `expires`, `http_only`, `secure`, `same_site`.
- `AccountRecord` dataclass with `account_id`, `cookie_source`, `status`, `pause_reason`.
- `parse_cookie_text(text: str, source: str) -> list[CookieRecord]`.
- `discover_accounts(cookie_dir: Path, single_cookie_file: Path | None = None) -> list[AccountRecord]`.
- `redact_cookie_value(value: str) -> str` must never expose the original value.

- [ ] **Step 1: Write failing tests** for semicolon, Netscape, JSON-array and `{cookies: [...]}` inputs; reject malformed entries; verify account IDs are stable file stems and redaction never contains the source value.
- [ ] **Step 2: Run** `pytest tests/test_taobao_browser_accounts.py -q`; expect failures because the module does not exist.
- [ ] **Step 3: Implement** strict parsers with UTF-8/UTF-8-SIG support, normalize domains to `.taobao.com`/`.tmall.com` when absent, and preserve cookie metadata needed by Playwright.
- [ ] **Step 4: Run** the focused test and confirm pass.
- [ ] **Step 5: Commit** `feat: add browser crawler account cookie parsing`.

### Task 2: Implement SQLite schema and resumable repository

**Files:** Create `src/taobao/browser/repository.py`, `tests/test_taobao_browser_repository.py`.

**Interfaces:**
- `BrowserCrawlerRepository(db_path: str | Path)` and `close()`.
- `create_run(input_source: str, options: dict) -> str` and `finish_run(run_id: str, summary: dict) -> None`.
- `upsert_account(account: AccountRecord) -> None`, `pause_account(account_id: str, reason: str) -> None`, `available_accounts() -> list[dict]`.
- `enqueue_keyword(keyword: str, platform: str, page_limit: int = 3, run_id: str | None = None) -> list[str]`.
- `enqueue_detail(platform: str, item_id: str, source_url: str | None, run_id: str | None = None) -> str`.
- `claim_next_task(account_id: str, now: str) -> dict | None`, `complete_task(task_id: str)`, `fail_task(task_id: str, error: str, retry_at: str | None)`, `pause_task(task_id: str, error: str)`.
- `recover_running_tasks() -> int`.
- `save_network_record(record: dict)`, `upsert_search_product(record: dict)`, `upsert_product_detail(record: dict)`, `upsert_comment(record: dict)`, `upsert_seller(record: dict)`.

- [ ] **Step 1: Write failing tests** for schema creation, unique keyword/page and platform/item constraints, run recovery, idempotent upserts, account pause, and task requeue.
- [ ] **Step 2: Run** `pytest tests/test_taobao_browser_repository.py -q`; expect missing-module failures.
- [ ] **Step 3: Implement** SQLite tables from the approved design with foreign keys, indexes on status/next_run_at, WAL mode for recovery, transactions around each logical write, and `INSERT ... ON CONFLICT DO UPDATE`.
- [ ] **Step 4: Run** focused tests and confirm duplicate writes do not increase row counts.
- [ ] **Step 5: Commit** `feat: add browser crawler sqlite repository`.

### Task 3: Add network capture redaction and JSON classification

**Files:** Create `src/taobao/browser/network_capture.py`, `tests/test_taobao_browser_network.py`, `tests/fixtures/taobao_browser/*.json`.

**Interfaces:**
- `redact_url(url: str) -> str`.
- `redact_headers(headers: Mapping[str, str]) -> dict[str, str]`.
- `try_parse_json(body: str, content_type: str | None) -> Any | None`.
- `classify_json(url: str, resource_type: str, payload: Any) -> str` returning `search/product_detail/comments/seller/unknown_json`.
- `build_network_record(meta: dict, body: str | None) -> dict`.

- [ ] **Step 1: Write failing tests** asserting secrets are removed from URL/headers/body metadata, malformed JSON is ignored, representative fixtures classify correctly, and unknown JSON remains persistable.
- [ ] **Step 2: Run** `pytest tests/test_taobao_browser_network.py -q`; expect failures.
- [ ] **Step 3: Implement** case-insensitive header/query redaction, bounded response-body handling, JSON content sniffing, and structural classification based on item/comment/seller ID keys rather than fixed endpoint names.
- [ ] **Step 4: Run** focused tests; inspect output to verify no fixture secret appears.
- [ ] **Step 5: Commit** `feat: classify and redact browser network payloads`.

### Task 4: Implement humanized behavior and risk detection

**Files:** Create `src/taobao/browser/human_behavior.py`, `src/taobao/browser/risk_control.py`, corresponding tests.

**Interfaces:**
- `DelayPolicy(min_seconds: float = 10.0, max_seconds: float = 30.0, seed: int | None = None)` with `sample() -> float` and `validate() -> None`.
- `async humanize_page(page, policy: DelayPolicy, rng=None) -> None` performing bounded wait, visible-area mouse movement, and 1–4 conditional scrolls.
- `classify_risk(url: str, title: str, body_text: str, status_code: int | None) -> str | None` returning `login_expired/challenge/rate_limited/forbidden/None`.

- [ ] **Step 1: Write failing tests** for delay bounds, invalid ranges, no forced scroll on short pages, risk markers and non-risk pages.
- [ ] **Step 2: Run** focused tests and observe failures.
- [ ] **Step 3: Implement** seeded random helpers for deterministic tests; use Playwright mouse move/scroll only in viewport, never click challenge controls; keep timing injectable so unit tests do not sleep.
- [ ] **Step 4: Run** tests and verify generated samples stay within bounds.
- [ ] **Step 5: Commit** `feat: add humanized pacing and risk detection`.

### Task 5: Build isolated Camoufox browser pool

**Files:** Create `src/taobao/browser/browser_pool.py`, extend account tests if needed.

**Interfaces:**
- `BrowserPool(accounts, headless=False, proxy=None, locale="zh-CN", max_instances=None)`.
- `async start_account(account_id: str) -> AccountBrowser`.
- `async stop_account(account_id: str) -> None`; `async close_all() -> None`.
- `AccountBrowser` exposes `browser`, `context`, `page`, `account_id` and `async install_cookies(cookies)`.

- [ ] **Step 1: Add failing tests** using a local fake browser adapter to assert each account gets a distinct context and cookies never cross contexts.
- [ ] **Step 2: Run** the focused tests and observe missing implementation.
- [ ] **Step 3: Implement** a small adapter around Camoufox/Playwright; default visible mode, pass `headless` only when requested, create one context per account, install parsed cookies before navigation, and close only that account on pause.
- [ ] **Step 4: Run** tests with the fake adapter; perform one manual local-page smoke test without visiting Taobao.
- [ ] **Step 5: Commit** `feat: isolate camoufox browser instances per account`.

### Task 6: Implement search/detail crawler and response persistence

**Files:** Create `src/taobao/browser/crawler.py`, `tests/test_taobao_browser_crawler.py`, local fixture handlers.

**Interfaces:**
- `CrawlerConfig` containing db path, account source, platforms, page limit, delay policy, headless, retry limit and optional keyword list.
- `BrowserCrawler(repository, browser_pool, config)`.
- `async run_keywords(keywords: list[str]) -> dict`.
- `async run_pending_tasks() -> dict`.
- `async crawl_search_page(task, account_browser) -> None`.
- `async crawl_detail(task, account_browser) -> None`.

- [ ] **Step 1: Write failing fixture-backed tests** for three search pages, all unique result items becoming detail tasks, detail payloads reaching the four tables, success skipping, and account-level risk requeue.
- [ ] **Step 2: Run** `pytest tests/test_taobao_browser_crawler.py -q`; expect failures.
- [ ] **Step 3: Implement** navigation for Taobao/Tmall search and item URLs, attach response listeners before navigation, capture only current-page requests, call `humanize_page` on every page, persist every redacted JSON record, enqueue unique details, and apply bounded task retries.
- [ ] **Step 4: Run** fixture tests; verify restart recovery and no duplicate detail rows.
- [ ] **Step 5: Commit** `feat: crawl taobao search and detail pages with browser capture`.

### Task 7: Add CLI and task-table input

**Files:** Create `src/taobao/browser/cli.py`, `tests/test_taobao_browser_cli.py`, update `src/taobao/browser/__init__.py`.

**Interfaces:**
- `build_arg_parser() -> argparse.ArgumentParser`.
- `config_from_args(args) -> CrawlerConfig`.
- `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write failing parser tests** for repeated `--keyword`, `--pages` default 3, `--from-tasks`, `--cookie-file`, `--cookie-dir`, `--db`, `--headless`, `--min-delay`, `--max-delay`, and `--search-only`.
- [ ] **Step 2: Run** focused tests and observe failures.
- [ ] **Step 3: Implement** both keyword and task-table modes, import a single `cookies.txt` as a test account when requested, reject an empty account pool or invalid delay range, and return nonzero only for system-level or uncompleted-run errors.
- [ ] **Step 4: Run** CLI tests and `python -m src.taobao.browser.cli --help`.
- [ ] **Step 5: Commit** `feat: add taobao browser crawler cli`.

### Task 8: Full verification and documentation

**Files:** Modify `README.md` only with a new browser-crawler section; add/adjust tests only when a demonstrated gap exists.

- [ ] **Step 1: Run** `pytest tests/test_taobao_browser_*.py -q` and the existing Taobao tests `pytest tests/test_taobao_search.py tests/test_taobao_item_get_from_search.py -q`.
- [ ] **Step 2: Run** CLI help and a local fixture end-to-end run using a temporary SQLite database; confirm no network call targets Taobao during tests.
- [ ] **Step 3: Verify** `git diff --check`, scan logs/database fixture output for Cookie, Authorization, Set-Cookie, token and sign values, and confirm unrelated worktree changes remain untouched.
- [ ] **Step 4: Document** account directory layout, CLI examples, schema location, pause/resume behavior and explicit manual verification requirement for real-site runs.
- [ ] **Step 5: Commit** `docs: document taobao browser crawler usage`.

---

## Execution Notes

- Each task must follow RED → GREEN → REFACTOR; do not write production code before its focused test fails.
- Use local fixtures for automated tests. A real-site smoke run, if performed, must use the provided account Cookie only with explicit user intent and must remain bounded.
- Do not call the metered `api-gw.fan-b.com` API for this browser-crawler feature.
- If browser startup or account login fails, preserve run/task state and report the exact paused account reason without exposing secrets.
