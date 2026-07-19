# Taobao Shop Crawler Design

## Goal

Build a lightweight Taobao shop item crawler for `https://api-gw.fan-b.com/taobao/item_search_shop_pro/` that reads API credentials from `password.env`, paginates automatically, saves progress promptly, and resumes interrupted crawls by `shop_id`.

## Scope

- Store credentials in `password.env` using existing `key` and `secret` entries.
- Use default `seller_id=2200684271326` and `shop_id=517932711`.
- Allow CLI overrides for `seller_id`, `shop_id`, max item count, database path, starting page, sort, language, cache flag, timeout, retry count, and request delay.
- Stop crawling when one of these happens:
  - saved item count for the current run reaches `--max-items`;
  - API page number exceeds `page_count`;
  - the API returns an empty item list;
  - the API reports a non-`0000` `error_code`;
  - repeated network/HTTP/JSON failures exceed retry settings.
- Persist each fetched page immediately to SQLite.
- Resume based only on `shop_id`, not `seller_id`.

## Architecture

The crawler will be a single Python module, `src/shop_crawler.py`, with small functions and one storage class:

- `load_env(path)` parses `password.env` without extra dependencies.
- `CrawlerConfig` holds CLI and runtime settings.
- `SQLiteStore` owns schema creation, item upsert, page recording, and state lookup.
- `fetch_page(config, page)` performs one HTTP request.
- `crawl_shop(config, fetcher=None)` coordinates resume, pagination, stopping, and persistence.
- `main()` exposes the CLI.

SQLite is the default store because it requires no running service, works well for local crawls, supports durable transactions, and gives natural unique constraints for item deduplication. Redis is not included because the current project is a local script workspace and does not need queue sharing.

## Data Model

`crawl_state`:

- `shop_id` primary key.
- `seller_id`, `next_page`, `fetched_items`, `page_count`, `total_results`, `status`, `last_error`, `updated_at`.

`shop_pages`:

- one row per saved `shop_id + page`.
- keeps item count, raw response JSON, and timestamps.

`shop_items`:

- primary key `num_iid`.
- stores shop and seller identifiers, title, prices, image URL, detail URL, shop name, first/last seen page, raw item JSON, and timestamps.

## Resume Rule

For a given `shop_id`, the crawler reads `crawl_state.next_page` and continues there unless `--reset` is provided. Existing `shop_items` rows are upserted by `num_iid`, so reruns are idempotent.

## Testing

Use Python `unittest` so the project has no test dependency. Tests cover env parsing, SQLite schema/upsert/resume behavior, page response parsing, and crawl stop conditions using an injected fake fetcher instead of real network calls.
