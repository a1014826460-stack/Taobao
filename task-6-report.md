# Task 6 report — search/detail crawler

Status: complete

## Implemented
- Added `src/taobao/browser/crawler.py` with `CrawlerConfig` and `BrowserCrawler`.
- Supports Taobao/Tmall search URL generation (up to configured page limit) and item detail navigation.
- Installs response listeners before navigation; captures bounded JSON responses through network redaction/classification and persists `network_records`.
- Normalizes search products, product details, comments, and seller payloads into repository tables; detail tasks are idempotently enqueued for unique items.
- Added round-robin account scheduling, bounded retries, resumable task completion/failure, account-level risk pause/requeue, and continuation on other accounts.
- Calls `humanize_page` for every visited page and supports injectable delay policy for tests.
- Fixed repository seller upsert placeholder count (schema has 8 columns).
- Added fixture-backed tests in `tests/test_taobao_browser_crawler.py` covering search→detail persistence and risk pause/requeue.

## Verification
- `$env:PYTHONPATH='src'; pytest -q tests/test_taobao_browser_crawler.py` — 2 passed.
- Existing browser tests (`accounts`, `repository`, `network`, `behavior`, `pool`, `pool_failure`) — 29 passed.

## Concerns / follow-up
- Real Camoufox/Playwright startup and site-specific payload schemas require manual verification; tests use local fake page/response fixtures and never access Taobao.
- Payload normalization is intentionally heuristic to accommodate changing endpoint shapes; unknown JSON is still retained in `network_records`.
