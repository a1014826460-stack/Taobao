# JD 商品评论采集 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为已成功的黄小米 JD 商品持久化采集第 1 页评论响应。

**Architecture:** 独立评论 SQLite 库保存原始响应和请求状态；评论模块从详情 SQLite 的成功状态读取 ID，并用 token 环境变量构建请求。默认续跑跳过成功项。

**Tech Stack:** Python 3、urllib、SQLite、unittest、PowerShell 7。

---

### Task 1: 评论模块与持久化

**Files:**
- Create: `src/jd/direct/comment.py`
- Create: `src/jd_comment_crawler.py`
- Test: `tests/test_jd_comment_crawler.py`

- [ ] **Step 1:** 写请求、状态持久化和续跑的失败测试。
- [ ] **Step 2:** 运行 `python -m pytest -q tests/test_jd_comment_crawler.py`，确认模块缺失导致失败。
- [ ] **Step 3:** 实现 `JDCommentCrawlerConfig`、SQLite 存储、请求与续跑逻辑。
- [ ] **Step 4:** 再次运行测试，确认通过。

### Task 2: 成功详情 ID 与 CLI

**Files:**
- Modify: `src/jd/direct/comment.py`
- Test: `tests/test_jd_comment_crawler.py`

- [ ] **Step 1:** 写从详情库读取成功 ID 的失败测试。
- [ ] **Step 2:** 实现详情加载和 `.env` 的 `JD_COMMENT_TOKEN` 读取，以及 CLI 参数。
- [ ] **Step 3:** 运行评论测试。

### Task 3: 单项验证及后台批量运行

**Files:**
- Modify: `.env`
- Read/Write: `data/jd_huangxiaomi_comments.sqlite3`
- Write: `target/jd_huangxiaomi_20260809/comment_run.log`

- [ ] **Step 1:** 将 token 写为 `JD_COMMENT_TOKEN`，不打印、不提交。
- [ ] **Step 2:** 用 `--limit 1` 真实请求，确认一条成功状态。
- [ ] **Step 3:** 后台启动剩余成功商品，并保留可恢复日志和状态。
