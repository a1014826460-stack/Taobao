# JD Search Pro Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic `jd/item_search_pro` fallback when the existing JD `item_search` request fails.

**Architecture:** Keep the existing `src.jd.direct.search` entry point and SQLite schema. Build normal requests against `https://api-gw.fan-b.com/jd/item_search/`; when fetching a page with the default fetcher fails after configured retries, build a pro request against `https://api-1.fan-b.com/jd/item_search_pro/` using the same query/filter/sort parameters and persist the successful response under the same query fingerprint.

**Tech Stack:** Python 3, `urllib.request`, SQLite, pytest/unittest.

---

### Task 1: Add request builder support for normal and pro endpoints

**Files:**
- Modify: `src/jd/direct/search.py`
- Test: `tests/test_jd_search.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting that `build_search_request(config, page)` still uses `/jd/item_search/`, that `build_search_request(config, page, api="item_search_pro")` uses `https://api-1.fan-b.com/jd/item_search_pro/`, and that empty `sort=""` is valid.

- [ ] **Step 2: Run tests and confirm failure**

Run: `python -m pytest -q tests/test_jd_search.py::JDSearchRequestAndParserTests`

Expected: tests for the new `api` argument fail with `TypeError` before implementation.

- [ ] **Step 3: Implement minimal endpoint selection**

Add constants for normal and pro URLs, allow `build_search_request(..., api="item_search")`, validate API names, and allow empty `sort`.

- [ ] **Step 4: Run tests and confirm pass**

Run: `python -m pytest -q tests/test_jd_search.py::JDSearchRequestAndParserTests`

### Task 2: Add fallback fetch behavior

**Files:**
- Modify: `src/jd/direct/search.py`
- Test: `tests/test_jd_search.py`

- [ ] **Step 1: Write failing tests**

Add tests for `fetch_search_page_with_fallback`: normal success does not call pro; normal failure after retries calls pro; pro receives same filters and succeeds.

- [ ] **Step 2: Run tests and confirm failure**

Run: `python -m pytest -q tests/test_jd_search.py::JDSearchRequestAndParserTests`

Expected: failure because `fetch_search_page_with_fallback` does not exist.

- [ ] **Step 3: Implement fallback helper and wire default crawler fetcher**

Create `fetch_search_page_with_fallback(config, page, opener=urlopen)` that calls `fetch_search_page(..., api="item_search")`; if it raises, calls `fetch_search_page(..., api="item_search_pro")`. Update `crawl_search` default fetcher to use the fallback helper.

- [ ] **Step 4: Run full JD search tests**

Run: `python -m pytest -q tests/test_jd_search.py`

### Task 3: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document fallback behavior**

Add one sentence to JD Keyword Search: when `jd/item_search` fails, the crawler retries the page through `jd/item_search_pro` with the same filters and sort values.

- [ ] **Step 2: Final verification**

Run: `python -m pytest -q tests/test_jd_search.py`

Expected: all JD search tests pass.
