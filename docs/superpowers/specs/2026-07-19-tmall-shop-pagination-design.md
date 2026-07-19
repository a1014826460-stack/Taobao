# Tmall Shop Pagination Crawler Design

## Goal

Add a standalone crawler for a Tmall shop's asynchronous product-list endpoint.
It obtains an authenticated cookie from the `TAOBAO_COOKIE` environment
variable, accepts the target shop URL and page range at runtime, saves products
and source pages to SQLite, and validates that all requested pages contain
distinct product IDs.

## Scope and Interface

The new module is separate from `src/tests/taobao_test.py`; that file remains a
small request experiment. The crawler exposes a Python API and a command-line
interface:

```powershell
$env:TAOBAO_COOKIE = 'name=value; name2=value2'
python src\tmall_shop_crawler.py `
  --shop-url 'https://iqoo.tmall.com/search.htm?orderType=defaultSort&viewType=grid' `
  --start-page 1 --pages 2
```

- `--start-page` and `--pages` are required, positive integers selected by the
  operator.
- `--db` defaults to `data/taobao_shop_items.sqlite3`.
- The crawler derives the asynchronous `/i/asynSearch.htm` URL from the shop
  URL and preserves the shop search parameters when building each page request.
- No cookie or other credential is embedded in source code, test fixtures, or
  SQLite output.

## Fetching and Parsing

Each request sends a browser-like user agent and `Referer`, with the cookie
parsed from `TAOBAO_COOKIE`. The response may be JSONP or JSON; the parser
unwraps JSONP before decoding it. Product data is extracted from the documented
response locations used by Tmall's async search payload, with explicit errors
when a usable product list or product ID is unavailable.

For every product, the crawler stores the normalized product ID, title, price,
original price, product URL, image URL, sales, current page number, raw product
JSON, and capture timestamp. Unknown fields stay in raw JSON rather than being
discarded.

## SQLite Persistence

The default SQLite database contains:

- `tmall_shop_pages`, keyed by shop URL and page, with item count, raw response
  JSON, and capture timestamp.
- `tmall_shop_items`, keyed by shop URL and product ID, with normalized fields,
  first and last observed pages, raw product JSON, and timestamps.

Writes for a successfully parsed page occur in one transaction. Re-running the
same range updates the page snapshot and item fields without creating duplicate
product rows.

## Validation and Failure Handling

The crawl validates every requested page as it is processed:

1. A non-2xx response, timeout, JSON/JSONP parse error, or missing product list
   fails the run.
2. An empty product list fails the run.
3. A product with no usable ID fails the run.
4. A product ID observed on more than one requested page fails the run.

The command prints per-page counts and a final result. Any validation failure
returns a non-zero exit code. A successfully stored earlier page is retained if
a later page fails, providing durable diagnostic data without falsely reporting
a successful full crawl.

## Testing and Verification

Offline `unittest` tests inject page responses and cover cookie parsing, JSONP
unwrapping, product normalization, SQLite upsert behavior, empty pages, and
cross-page duplicate-ID failure. The live verification command requests the
operator-selected range; it requires `TAOBAO_COOKIE` to be set and confirms
that each page produces products and that the requested pages have no shared
product IDs.
