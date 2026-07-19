# Taobao Shop Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight resumable Taobao shop item crawler that reads credentials from `password.env`, paginates the Fan-B API, and persists results to SQLite.

**Architecture:** Add a focused CLI module at `src/shop_crawler.py`. Keep networking, storage, response parsing, and orchestration behind testable functions/classes, with resume state keyed only by `shop_id`.

**Tech Stack:** Python standard library only: `argparse`, `dataclasses`, `json`, `sqlite3`, `time`, `urllib.request`, `urllib.parse`, `unittest`.

---

### Task 1: Tests for Credentials and SQLite State

**Files:**
- Create: `tests/test_shop_crawler.py`
- Create: `src/shop_crawler.py`

- [ ] **Step 1: Write failing tests**

Create tests that import `load_env` and `SQLiteStore`, assert env parsing, item upsert, and resume state keyed by `shop_id`.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.test_shop_crawler -v`
Expected: import failure because `src.shop_crawler` does not exist.

- [ ] **Step 3: Implement minimal env and SQLite code**

Create `src/shop_crawler.py` with `load_env`, `SQLiteStore`, and schema methods.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m unittest tests.test_shop_crawler -v`
Expected: tests pass for env parsing and persistence.

### Task 2: Tests for Crawl Pagination and Stop Limits

**Files:**
- Modify: `tests/test_shop_crawler.py`
- Modify: `src/shop_crawler.py`

- [ ] **Step 1: Write failing tests**

Add fake fetcher tests for `crawl_shop`: automatic page increment, stop at `max_items`, stop at `page_count`, and resume from stored `next_page` by `shop_id`.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.test_shop_crawler -v`
Expected: failures because crawl orchestration is missing.

- [ ] **Step 3: Implement crawl orchestration**

Add `CrawlerConfig`, `parse_items_response`, `crawl_shop`, and request stop/status handling.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m unittest tests.test_shop_crawler -v`
Expected: all unit tests pass.

### Task 3: CLI and Real HTTP Fetcher

**Files:**
- Modify: `tests/test_shop_crawler.py`
- Modify: `src/shop_crawler.py`

- [ ] **Step 1: Write failing tests**

Add tests for argument parsing defaults and HTTP request URL construction using a fake opener.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.test_shop_crawler -v`
Expected: failures because CLI and fetcher code is missing.

- [ ] **Step 3: Implement CLI and fetcher**

Add `build_arg_parser`, `config_from_args`, `fetch_page`, and `main`.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m unittest tests.test_shop_crawler -v`
Expected: all tests pass.

### Task 4: Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run unit tests**

Run: `python -m unittest tests.test_shop_crawler -v`
Expected: all tests pass.

- [ ] **Step 2: Run CLI help**

Run: `python src/shop_crawler.py --help`
Expected: help text shows crawler options and exits with code 0.

- [ ] **Step 3: Report usage**

Show a normal command:

```powershell
python src/shop_crawler.py --max-items 100
```

Show a resume command:

```powershell
python src/shop_crawler.py --shop-id 517932711 --max-items 200
```
