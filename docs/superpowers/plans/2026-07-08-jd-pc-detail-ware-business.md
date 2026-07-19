# JD PC Detail WareBusiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable Node.js script that accepts a JD skuId, generates the `h5st` signed `pc_detailpage_wareBusiness` request through the official browser signing context, and saves the product detail API response.

**Architecture:** Split pure request-building helpers from browser/network orchestration. Unit-test deterministic helpers first, then use Playwright for dynamic JD page context and `window.PSign.sign`/compatible signing paths. Keep Cookie outside source code; read it from `JD_COOKIE` or a `--cookie` argument only at runtime.

**Tech Stack:** Node.js 22, Playwright, built-in `node:test`, built-in `fetch`, PowerShell for verification.

---

### Task 1: Pure URL/body helpers

**Files:**
- Create: `src/tests/jd_pc_detail_ware_business.js`
- Create: `tests/jd_pc_detail_ware_business.test.js`

- [ ] Write failing tests for skuId extraction, stable body JSON construction, and API URL query construction.
- [ ] Run `node --test tests/jd_pc_detail_ware_business.test.js` and verify failures are caused by missing exports.
- [ ] Implement the minimal helper functions: `extractSkuId`, `buildWareBusinessBody`, `stableJsonStringify`, `buildUnsignedApiUrl`.
- [ ] Re-run tests and verify they pass.

### Task 2: Browser signing orchestration

**Files:**
- Modify: `src/tests/jd_pc_detail_ware_business.js`

- [ ] Add CLI parsing for `skuId`, `--area`, `--output-dir`, `--headless`, `--cookie`.
- [ ] Launch Chromium with Playwright, optionally inject Cookie, open `https://item.jd.com/<skuId>.html`.
- [ ] Wait for JD scripts to expose `window.PSign` or compatible `ParamsSign` path.
- [ ] Call signing code inside browser context with `appid=item-v3`, `functionId=pc_detailpage_wareBusiness`, `body=<stable JSON>`, `client=pc`, `clientVersion=1.0.0`, `t=<timestamp>`.
- [ ] Build final API URL from signed params.

### Task 3: Fetch and save response

**Files:**
- Modify: `src/tests/jd_pc_detail_ware_business.js`

- [ ] Use Playwright browser-context request first, falling back to Node `fetch` with browser-like headers.
- [ ] Save raw JSON/text response to `data/jd_reverse/items/<skuId>.wareBusiness.json`.
- [ ] Print compact summary fields when JSON parsing succeeds.
- [ ] Redact Cookie values from logs and errors.

### Task 4: Verification

**Files:**
- Verify: `tests/jd_pc_detail_ware_business.test.js`
- Verify: `data/jd_reverse/items/10207466352379.wareBusiness.json`

- [ ] Install Playwright if absent with `npm install --save-dev playwright`.
- [ ] Run unit tests.
- [ ] Run one live request with the user-approved Cookie in `JD_COOKIE`.
- [ ] Inspect saved response for JD API success/error shape and report findings.

## Self-review

- Covers requested variable product ID script, detail API, h5st dynamic generation, Cookie runtime handling, and one live test.
- No hard-coded Cookie in source files.
- No irreversible actions.
