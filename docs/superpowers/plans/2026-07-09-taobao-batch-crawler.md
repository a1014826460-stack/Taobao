# Taobao Batch Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a batch Taobao/Tmall item-detail crawler that accepts item IDs, extracts SSR `loaderData`, stores results in SQLite, and resumes from prior successes.

**Architecture:** `src/tests/taobao_batch.py` owns CLI parsing, HTTP fetching, HTML `window.__ICE_APP_CONTEXT__` extraction, normalized summary fields, SQLite persistence, and batch control. It reuses the SSL/proxy fix from `taobao_test.py` by using `Session.trust_env = False`.

**Tech Stack:** Python 3, requests, sqlite3, unittest.

---

### Task 1: Parser and SQLite Tests

**Files:**
- Create: `tests/test_taobao_batch.py`
- Create: `src/tests/taobao_batch.py`

- [ ] Write tests for ID parsing, loaderData extraction from inline HTML, SQLite save/skip semantics.
- [ ] Run tests and verify failure because module does not exist.
- [ ] Implement minimal batch module.
- [ ] Run tests and verify pass.

### Task 2: Batch Run

**Files:**
- Create: `data/taobao_requested_ids.txt`
- Output: `data/taobao_items.sqlite3`

- [ ] Save requested IDs into file.
- [ ] Run `python src/tests/taobao_batch.py --ids-file data/taobao_requested_ids.txt --db data/taobao_items.sqlite3 --delay-min 2 --delay-max 5`.
- [ ] Verify SQLite success count and report failures.
