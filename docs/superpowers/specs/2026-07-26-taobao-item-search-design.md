# Taobao Item Search Crawler Design

## Goal

Provide a standalone, resumable Taobao keyword-search crawler that requests
Fan-B's `item_search` API concurrently, orders results by sales by default,
and persists both page snapshots and normalized search items in SQLite.

## Interface And Fetching

`python -m src.taobao.direct.search` accepts a required `--q` keyword and a
positive `--max-pages` limit. It crawls page 1 through that limit, with four
workers by default and an overridable `--workers` value. The default sort is
`_sale`; callers can pass price bounds and supported search filters. Gateway
credentials come from `FANB_API_KEY`/`FANB_API_SECRET` (or `KEY`/`SECRET`) in
the environment or project `.env` file.

Each request includes the supplied API parameters plus `page`, `lang=zh-CN`,
and `cache=no`. Requests retry transient failures with backoff. `--delay`
sets the minimum global interval between requests to avoid bursting the
gateway despite concurrent workers.

## Persistence And Resume

The default database is `data/taobao_search.sqlite3`. `search_pages` stores a
query fingerprint, page number, item count, full response JSON, and capture
timestamps. `search_items` stores each result's normalized item ID, title,
prices, sales, shop, URL, image, first/last seen page, raw item JSON, and
timestamps. `search_state` records page status and last errors.

The query fingerprint is a deterministic JSON representation of the keyword
and filters, excluding pagination and credentials. A rerun skips only pages
whose state is `success` for the same fingerprint; failed pages resume. A
successful page writes its page snapshot, item upserts, and state atomically.
Items are deduplicated by fingerprint and item ID.

## Validation And Completion

Responses must be JSON objects with no nonzero API `error_code`, an `items`
object, and an `items.item` list. Empty pages are valid successful snapshots
because the page limit is explicit. Item records without a usable ID are
stored only in the page raw JSON and do not create normalized rows.

The CLI prints aggregate page/item/failure counts and exits nonzero if any
page failed. It never performs `item_get`; persisted data is only the
`item_search` response.

## Testing

Offline unit tests inject fetchers to cover request construction, API response
validation, transactional SQLite upsert/resume behavior, and concurrent page
execution. Tests run without gateway credentials or network access.
