# Item Detail API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate item detail crawler API with resumable SQLite persistence and a shared CLI entry point.

**Architecture:** Create `src/item_crawler.py` for item-detail-specific config, fetching, parsing, storage, and crawl orchestration. Modify `src/shop_crawler.py` only for CLI dispatch so `shop` and `item` remain separate API implementations.

**Tech Stack:** Python standard library: `argparse`, `dataclasses`, `json`, `sqlite3`, `time`, `urllib.request`, `urllib.parse`, `unittest`.

---

### Task 1: Item ID Input and Storage

**Files:**
- Create: `src/item_crawler.py`
- Modify: `tests/test_shop_crawler.py`

- [ ] Write failing tests for `parse_num_iids` and `SQLiteItemStore`.
- [ ] Run `python -m unittest tests.test_shop_crawler -v` and confirm missing imports fail.
- [ ] Implement `parse_num_iids`, `ItemCrawlerConfig`, `ItemCrawlResult`, and `SQLiteItemStore`.
- [ ] Run the tests and confirm the new storage/input tests pass.

### Task 2: Item Crawl Orchestration

**Files:**
- Modify: `src/item_crawler.py`
- Modify: `tests/test_shop_crawler.py`

- [ ] Write failing tests for `crawl_items`: saves details, skips successful IDs on resume, and refetches with `reset_items`.
- [ ] Run tests and confirm orchestration failures.
- [ ] Implement `parse_item_response`, `crawl_items`, and status persistence.
- [ ] Run tests and confirm pass.

### Task 3: Item Fetcher and Shared CLI

**Files:**
- Modify: `src/item_crawler.py`
- Modify: `src/shop_crawler.py`
- Modify: `tests/test_shop_crawler.py`

- [ ] Write failing tests for `fetch_item_detail` URL construction and `item` CLI config creation.
- [ ] Run tests and confirm failures.
- [ ] Implement `fetch_item_detail`, subcommands, item config creation, and compatibility default to `shop`.
- [ ] Run tests and confirm pass.

### Task 4: Final Verification

**Files:**
- No new files.

- [ ] Run `python -m unittest tests.test_shop_crawler -v`.
- [ ] Run `python src\shop_crawler.py --help`.
- [ ] Run `python src\shop_crawler.py item --help`.
- [ ] Run `python -m compileall src tests`.
