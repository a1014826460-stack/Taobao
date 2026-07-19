# Tmall Shop Pagination Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Tmall shop async-product crawler that persists an operator-selected page range to SQLite and fails when any requested page is invalid, empty, or shares a product ID with another requested page.

**Architecture:** `src/tmall_shop_crawler.py` will keep transport, JSONP parsing, product normalization, SQLite persistence, validation, and CLI entry points in one focused module, matching the project's existing lightweight `requests`/`sqlite3` scripts. `tests/test_tmall_shop_crawler.py` will supply fake responses and a temporary database, so all behavior apart from the final live request is deterministic and offline.

**Tech Stack:** Python 3, `requests`, `sqlite3`, `unittest`.

---

## File Structure

- Create: `src/tmall_shop_crawler.py` - request construction, response parsing, persistence, crawl orchestration, and CLI.
- Create: `tests/test_tmall_shop_crawler.py` - offline tests for parsing, storage, validation, and CLI configuration.
- Create: `.gitignore` - excludes Python caches, virtual environments, credentials, generated crawl databases, and local run artifacts.
- Create: `docs/superpowers/plans/2026-07-19-tmall-shop-pagination-crawler.md` - this implementation plan.

### Task 1: Write the Parser and Request-Configuration Tests

**Files:**
- Create: `tests/test_tmall_shop_crawler.py`
- Create: `src/tmall_shop_crawler.py`

- [ ] **Step 1: Add a failing parser/configuration test module**

Create `tests/test_tmall_shop_crawler.py` with these initial tests:

```python
import json
import unittest

from src import tmall_shop_crawler


class TmallRequestAndParserTests(unittest.TestCase):
    def test_parse_cookie_header_ignores_malformed_segments(self):
        self.assertEqual(
            tmall_shop_crawler.parse_cookie_header('a=1; invalid; b=two=parts; =missing'),
            {'a': '1', 'b': 'two=parts'},
        )

    def test_build_page_request_uses_shop_search_and_page_number(self):
        request_url, params, headers = tmall_shop_crawler.build_page_request(
            'https://iqoo.tmall.com/search.htm?orderType=defaultSort&viewType=grid',
            2,
        )
        self.assertEqual(request_url, 'https://iqoo.tmall.com/i/asynSearch.htm')
        self.assertEqual(params['path'], '/search.htm')
        self.assertEqual(params['orderType'], 'defaultSort')
        self.assertEqual(params['viewType'], 'grid')
        self.assertEqual(params['pageNo'], '2')
        self.assertEqual(headers['Referer'], 'https://iqoo.tmall.com/search.htm?orderType=defaultSort&viewType=grid')

    def test_decode_jsonp_and_extract_product_fields(self):
        payload = {'itemList': [{'item_id': '1001', 'title': 'Test item', 'price': '9.90'}]}
        parsed = tmall_shop_crawler.decode_payload('jsonp91(' + json.dumps(payload) + ');')
        items = tmall_shop_crawler.extract_products(parsed, 1)
        self.assertEqual(items[0]['item_id'], '1001')
        self.assertEqual(items[0]['title'], 'Test item')
        self.assertEqual(items[0]['page_number'], 1)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the initial tests and verify they fail because the crawler module is missing**

Run:

```powershell
python -m unittest tests.test_tmall_shop_crawler -v
```

Expected: test collection fails with `ImportError` because `src.tmall_shop_crawler` does not exist.

- [ ] **Step 3: Add the minimal parser and request-configuration implementation**

Create `src/tmall_shop_crawler.py` with `parse_cookie_header`, `build_page_request`, `decode_payload`, and `extract_products`. `build_page_request` must require a `tmall.com` shop URL, construct `/i/asynSearch.htm` on the same host, preserve `orderType`, `viewType`, `keyword`, `lowPrice`, and `highPrice`, and add `pageNo`, `search=y`, `path=/search.htm`, and a JSONP callback. `decode_payload` must accept either a JSON object or one JSONP callback wrapper. `extract_products` must find lists at `itemList`, `data.itemList`, `itemDOList`, `data.itemDOList`, `mods.itemList.data.auctions`, or `mods.itemList.data.items`; normalize supported ID keys (`item_id`, `itemId`, `nid`, `id`) and common title/price/image/link/sales keys; and reject missing IDs or missing lists.

- [ ] **Step 4: Run the parser/configuration tests and verify they pass**

Run:

```powershell
python -m unittest tests.test_tmall_shop_crawler -v
```

Expected: 3 tests pass.

### Task 2: Add Transactional SQLite Storage

**Files:**
- Modify: `tests/test_tmall_shop_crawler.py`
- Modify: `src/tmall_shop_crawler.py`

- [ ] **Step 1: Add a failing SQLite upsert test**

Append this test, importing `tempfile` and `Path` as needed:

```python
def test_store_page_upserts_items_and_raw_page(self):
    with tempfile.TemporaryDirectory() as directory:
        store = tmall_shop_crawler.TmallShopStore(Path(directory) / 'shop.sqlite3')
        store.save_page(
            shop_url='https://iqoo.tmall.com/search.htm',
            page_number=1,
            raw_payload={'itemList': [{'item_id': '1001'}]},
            items=[{'item_id': '1001', 'title': 'Old title', 'page_number': 1}],
        )
        store.save_page(
            shop_url='https://iqoo.tmall.com/search.htm',
            page_number=1,
            raw_payload={'itemList': [{'item_id': '1001'}]},
            items=[{'item_id': '1001', 'title': 'New title', 'page_number': 1}],
        )
        self.assertEqual(store.count_pages(), 1)
        self.assertEqual(store.count_items(), 1)
        self.assertEqual(store.get_item('https://iqoo.tmall.com/search.htm', '1001')['title'], 'New title')
        store.close()
```

- [ ] **Step 2: Run the SQLite test and verify it fails because `TmallShopStore` is absent**

Run:

```powershell
python -m unittest tests.test_tmall_shop_crawler.TmallRequestAndParserTests.test_store_page_upserts_items_and_raw_page -v
```

Expected: FAIL with `AttributeError` for `TmallShopStore`.

- [ ] **Step 3: Implement `TmallShopStore` with atomic page saves**

Add `TmallShopStore` with a parent-directory-creating SQLite connection and the two tables specified in the design:

```sql
CREATE TABLE IF NOT EXISTS tmall_shop_pages (
    shop_url TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    item_count INTEGER NOT NULL,
    raw_json TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    PRIMARY KEY (shop_url, page_number)
);
CREATE TABLE IF NOT EXISTS tmall_shop_items (
    shop_url TEXT NOT NULL,
    item_id TEXT NOT NULL,
    title TEXT,
    price TEXT,
    original_price TEXT,
    item_url TEXT,
    image_url TEXT,
    sales TEXT,
    first_seen_page INTEGER NOT NULL,
    last_seen_page INTEGER NOT NULL,
    raw_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (shop_url, item_id)
);
```

`save_page` must use one `with self.conn:` transaction to upsert a page snapshot and all normalized items. It must retain the original `first_seen_page`, update `last_seen_page`, replace fields with the current data, serialize JSON with `ensure_ascii=False`, and expose `count_pages`, `count_items`, `get_item`, and `close` for tests and diagnostics.

- [ ] **Step 4: Run all crawler tests and verify storage behavior passes**

Run:

```powershell
python -m unittest tests.test_tmall_shop_crawler -v
```

Expected: 4 tests pass.

### Task 3: Add Range Crawling and Cross-Page Validation

**Files:**
- Modify: `tests/test_tmall_shop_crawler.py`
- Modify: `src/tmall_shop_crawler.py`

- [ ] **Step 1: Add failing crawl validation tests using an injected fetcher**

Append tests that use this helper and assert the stated outcomes:

```python
def fake_fetcher(page_number):
    return {'itemList': [{'item_id': str(page_number), 'title': f'page {page_number}'}]}

result = tmall_shop_crawler.crawl_pages(
    shop_url='https://iqoo.tmall.com/search.htm',
    start_page=1,
    pages=2,
    fetcher=fake_fetcher,
    store=store,
)
self.assertEqual(result.page_item_counts, {1: 1, 2: 1})
self.assertEqual(result.total_items, 2)
```

Add separate tests that pass an empty `itemList` on page 2 and the same `item_id` on pages 1 and 2. Each must assert `tmall_shop_crawler.CrawlValidationError` and verify the duplicate case names the duplicated ID.

- [ ] **Step 2: Run the new crawl tests and verify they fail because crawl orchestration is absent**

Run:

```powershell
python -m unittest tests.test_tmall_shop_crawler -v
```

Expected: FAIL with `AttributeError` for `crawl_pages` or `CrawlValidationError`.

- [ ] **Step 3: Implement crawl orchestration with strict validation**

Add `CrawlValidationError`, immutable `CrawlResult`, and `crawl_pages(shop_url, start_page, pages, fetcher, store)`. Reject non-positive range values before fetching. For every requested page, call the injected fetcher, normalize it with `extract_products`, reject an empty list, compare each ID against all prior requested pages, and only then call `store.save_page`. Return `CrawlResult(page_item_counts={...}, total_items=...)`. Do not swallow exceptions: a request, parse, empty-page, missing-ID, or duplicate-ID error must halt the crawl and let `main` return a non-zero code.

- [ ] **Step 4: Run the crawler test module and verify all validation tests pass**

Run:

```powershell
python -m unittest tests.test_tmall_shop_crawler -v
```

Expected: all crawler tests pass, including successful two-page storage, empty-page rejection, and cross-page duplicate rejection.

### Task 4: Add HTTP Fetching, CLI, and Repository Ignore Rules

**Files:**
- Modify: `tests/test_tmall_shop_crawler.py`
- Modify: `src/tmall_shop_crawler.py`
- Create: `.gitignore`

- [ ] **Step 1: Add failing environment and CLI tests**

Add tests which patch `os.environ` to assert that `config_from_args` raises `ValueError` when `TAOBAO_COOKIE` is missing and creates a configuration when it contains `a=1; b=2`. Add a `FakeSession` whose `get` method returns a response with `status_code=200` and JSONP content; assert `fetch_page` uses `session.trust_env = False`, passes parsed cookies, uses the configured timeout, and returns the decoded payload. Add a test that `main([...])` returns `1` when no cookie environment variable is set.

- [ ] **Step 2: Run the environment and HTTP tests and verify they fail**

Run:

```powershell
python -m unittest tests.test_tmall_shop_crawler -v
```

Expected: FAIL because `config_from_args`, `fetch_page`, and `main` are not yet implemented.

- [ ] **Step 3: Implement CLI and real HTTP fetcher**

Add `CrawlerConfig`, `parse_args`, `config_from_args`, `build_session`, `fetch_page`, `configure_stdout_utf8`, and `main`. The CLI must require `--shop-url`, `--start-page`, and `--pages`; accept `--db` and `--timeout`; read only `TAOBAO_COOKIE`; print each saved page count plus final total; return `1` to stderr for expected configuration, HTTP, JSONP/JSON, empty-page, or duplicate validation errors. `fetch_page` must call `response.raise_for_status()` and decode the returned text before persistence. The `__main__` guard must call `raise SystemExit(main())`.

Create `.gitignore` containing:

```gitignore
# Python bytecode and test caches
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/

# Local environments and secrets
.venv/
venv/
env/
*.env
password.env

# Generated crawl data and temporary files
data/*.sqlite3
data/*.sqlite3-*
data/taobao_html/
*.log

# Editor and operating-system files
.vscode/
.idea/
.DS_Store
Thumbs.db
```

- [ ] **Step 4: Run all tests, CLI help, and static compilation**

Run:

```powershell
python -m unittest discover -s tests -v
python -m py_compile src\tmall_shop_crawler.py
python src\tmall_shop_crawler.py --help
```

Expected: the full test suite is green, compilation exits 0, and help displays required `--shop-url`, `--start-page`, and `--pages` options.

### Task 5: Verify a Live Two-Page Crawl

**Files:**
- Output: `data/taobao_shop_items.sqlite3`

- [ ] **Step 1: Check that runtime credentials are available without displaying them**

Run:

```powershell
if ([string]::IsNullOrWhiteSpace($env:TAOBAO_COOKIE)) { Write-Error 'TAOBAO_COOKIE is not set'; exit 1 }
Write-Output 'TAOBAO_COOKIE is set.'
```

Expected: the command reports the variable is set without logging its value.

- [ ] **Step 2: Run the operator-authorized two-page crawl**

Run:

```powershell
python src\tmall_shop_crawler.py `
  --shop-url 'https://iqoo.tmall.com/search.htm?orderType=defaultSort&viewType=grid' `
  --start-page 1 `
  --pages 2 `
  --db data\taobao_shop_items.sqlite3
```

Expected: one non-empty count for each of pages 1 and 2, distinct IDs across the range, a final total, and exit code 0.

- [ ] **Step 3: Independently verify the SQLite output**

Run:

```powershell
@'
import sqlite3
db = sqlite3.connect('data/taobao_shop_items.sqlite3')
pages = db.execute('SELECT page_number, item_count FROM tmall_shop_pages ORDER BY page_number').fetchall()
duplicates = db.execute('''
    SELECT item_id, COUNT(*)
    FROM tmall_shop_items
    GROUP BY shop_url, item_id
    HAVING COUNT(*) > 1
''').fetchall()
print(f'pages={pages}')
print(f'item_rows={db.execute("SELECT COUNT(*) FROM tmall_shop_items").fetchone()[0]}')
print(f'duplicate_rows={duplicates}')
'@ | python -
```

Expected: records for pages 1 and 2, a positive item-row count, and `duplicate_rows=[]`.

- [ ] **Step 4: Initialize Git only if the operator explicitly requests it**

Do not run `git init` as part of this task. The `.gitignore` file is ready for the repository once the operator chooses the repository's Git initialization and remote settings.

## Plan Self-Review

- Spec coverage: Tasks 1 and 4 implement `TAOBAO_COOKIE`, page URL construction, JSON/JSONP decoding, CLI selection, HTTP errors, and non-zero error exits. Task 2 implements both SQLite tables and atomic upserts. Task 3 implements non-empty-page and cross-page duplicate validation. Task 5 performs the requested live two-page verification and independent database check.
- Placeholder scan: the plan contains no unfinished markers or generic implementation-only steps; code and commands are supplied for every planned change.
- Type consistency: `extract_products` returns normalized item dictionaries consumed by `TmallShopStore.save_page`; `crawl_pages` returns `CrawlResult`; `fetch_page` returns decoded dictionaries to the crawl fetcher; all call sites use `page_number` and `item_id` consistently.
