# Taobao Item Search Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a resumable concurrent `item_search` crawler which stores raw page snapshots and normalized search items in SQLite.

**Architecture:** A new `src.taobao.direct.search` module owns gateway request construction, response validation, SQLite persistence, concurrent page orchestration, and its CLI. `tests/test_taobao_search.py` injects responses into the public crawler API so storage and concurrency behavior are deterministic and offline.

**Tech Stack:** Python 3 standard library (`argparse`, `concurrent.futures`, `sqlite3`, `urllib`), `unittest`.

---

## File Structure

- Create: `src/taobao/direct/search.py` - search API client, SQLite store, concurrent crawler, and CLI.
- Create: `tests/test_taobao_search.py` - offline unit tests.
- Modify: `README.md` - runnable item-search usage example.

### Task 1: Define And Test Search Request/Response Boundaries

- [ ] Write failing tests for default `_sale` request parameters and response validation.
- [ ] Run the focused tests and observe the expected missing-module failure.
- [ ] Implement `SearchCrawlerConfig`, `build_search_request`, and `parse_search_response`.
- [ ] Re-run the focused tests and observe success.

### Task 2: Add Transactional SQLite Search Storage

- [ ] Write a failing test that saves a page twice and asserts one page and one updated item row.
- [ ] Run it and observe the expected missing-store failure.
- [ ] Implement `SQLiteSearchStore` tables, atomic page/item/state upserts, and resume state lookup.
- [ ] Re-run the focused storage tests and observe success.

### Task 3: Implement Concurrent, Resumable Page Crawling

- [ ] Write failing tests with an injected fetcher for max-page fan-out, failed-page reporting, and skipping prior success.
- [ ] Run the focused tests and observe the expected missing-orchestrator failure.
- [ ] Implement bounded thread-pool execution, global request throttling, retrying gateway fetches, and `SearchCrawlResult`.
- [ ] Re-run all search tests and observe success.

### Task 4: Expose CLI And Documentation

- [ ] Add CLI tests for required keyword/page validation and credential loading as needed.
- [ ] Implement the CLI flags and `__main__` entry point.
- [ ] Document safe credential configuration and examples in README.
- [ ] Run all Python tests, compile the new module, and inspect CLI help.
