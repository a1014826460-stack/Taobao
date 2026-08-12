# JD Phase 2 Search and Detail Top-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand JD search coverage for the 19 keywords in controlled batches, then dedupe and top up JD detail pages toward 200 successes per keyword.

**Architecture:** Reuse `src/jd/direct/search.py` for resumable search expansion with `item_search -> item_search_pro` fallback, persist into `data/jd_search.sqlite3`, then generate globally deduped detail candidates and crawl them via `src/jd/direct/item.py` into `data/jd_item_details.sqlite3`. Track per-keyword attribution through `jd_item_sources` and stop immediately on billing/auth errors such as `4016`.

**Tech Stack:** Python, SQLite, PowerShell 7, Fan-B JD APIs, repo target scripts/logs.

---

### Task 1: Inspect local state and set bounded batch scope

**Files:**
- Read: `AGENTS.md`
- Read: `src/jd/direct/search.py`
- Read: `src/jd/direct/item.py`
- Read/Write: `target/jd_detail_19_keywords_20260729/current_summary.csv`

- [ ] Step 1: Query current search/detail coverage from local SQLite DBs.
- [ ] Step 2: Rank weak keywords by current per-keyword success and source coverage.
- [ ] Step 3: Cap the next search batch to bounded sort/page combinations only.

### Task 2: Run controlled JD search expansion

**Files:**
- Read/Write: `data/jd_search.sqlite3`
- Write: `target/jd_detail_19_keywords_20260729/search_phase2_round*.log`
- Optional Write: `target/run_jd_search_phase2_round*.py`

- [ ] Step 1: Execute bounded search batches for weak keywords first.
- [ ] Step 2: Use existing resumable state so only non-success pages are retried.
- [ ] Step 3: Stop immediately if `4016` or equivalent billing/auth failures appear.

### Task 3: Generate deduped detail candidates and top up details

**Files:**
- Read: `data/jd_search.sqlite3`
- Read/Write: `data/jd_item_details.sqlite3`
- Write: `target/jd_detail_19_keywords_20260729/phase2_round*_detail_candidates.csv`
- Write: `target/jd_detail_19_keywords_20260729/detail_run_phase2_round*.log`

- [ ] Step 1: Generate candidate IDs from newly available search pages.
- [ ] Step 2: Deduplicate globally before detail requests.
- [ ] Step 3: Crawl details with bounded concurrency/retries and source attribution.

### Task 4: Recompute progress and prepare next round / upload handoff

**Files:**
- Read/Write: `target/jd_detail_19_keywords_20260729/current_summary.csv`
- Write: `target/jd_detail_19_keywords_20260729/phase2_round*_summary.csv`

- [ ] Step 1: Recompute per-keyword success, gap, and source counts.
- [ ] Step 2: Decide whether another bounded search round is needed.
- [ ] Step 3: Report generated artifacts and upload-ready increments.
