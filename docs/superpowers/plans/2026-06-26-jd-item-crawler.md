# JD Item Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone JD item detail crawler with SQLite persistence and resumable item-level state.

**Architecture:** Add `src/jd_item_crawler.py` as a focused script containing parsing, config, HTTP fetch, SQLite store, crawl loop, and CLI entrypoint. Add `tests/test_jd_item_crawler.py` to verify behavior with injected fetchers and fake HTTP openers.

**Tech Stack:** Python standard library: `argparse`, `dataclasses`, `json`, `sqlite3`, `urllib.request`, `unittest`.

---

### Task 1: JD Item Crawler Tests

**Files:**
- Create: `tests/test_jd_item_crawler.py`
- Create: `src/jd_item_crawler.py`

- [ ] **Step 1: Write failing tests**

Add tests for parsing, SQLite persistence, resume behavior, URL construction, config, and script help.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m unittest tests.test_jd_item_crawler -v
```

Expected: fail because `src.jd_item_crawler` is not implemented.

- [ ] **Step 3: Implement minimal crawler**

Create `src/jd_item_crawler.py` with:

- `parse_num_iids`
- `load_env`
- `JDItemCrawlerConfig`
- `JDItemCrawlResult`
- `SQLiteJDItemStore`
- `parse_jd_item_response`
- `fetch_jd_item_detail`
- `crawl_jd_items`
- CLI parser and `main`

- [ ] **Step 4: Run focused tests**

Run:

```bash
python -m unittest tests.test_jd_item_crawler -v
```

Expected: all JD crawler tests pass.

- [ ] **Step 5: Run full test suite**

Run:

```bash
python -m unittest discover -v
```

Expected: all tests pass.
