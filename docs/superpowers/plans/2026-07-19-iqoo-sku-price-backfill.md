# iQOO SKU Price Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill exact iQOO SKU prices and explicit interest-free installment values into a copied workbook, supplementing local details only from the captured shop list and reporting every unfilled result.

**Architecture:** A focused `src/iqoo_sku_price_backfill.py` module will parse workbook rows, extract normalized SKU information from the existing detail database, choose candidate shop items by model text, delegate missing detail collection to `src.taobao_batch`, and write the filled and report workbooks. Tests use temporary SQLite databases and workbooks, with injected batch fetch behavior so matching and report logic are offline and deterministic.

**Tech Stack:** Python 3, `openpyxl`, `sqlite3`, `unittest`, existing `src.taobao_batch`.

---

### Task 1: Write Exact-SKU Matching Tests

**Files:**
- Create: `tests/test_iqoo_sku_price_backfill.py`
- Create: `src/iqoo_sku_price_backfill.py`

- [ ] **Step 1: Create a failing test for exact three-field SKU matching**

Add a test that passes a detail record with three SKU choices and asserts only
the exact `model`, `configuration`, and `color` tuple returns the right price:

```python
detail = {
    'item_id': '1001',
    'title': 'iQOO 15 phone',
    'sku_base': {
        'props': [
            {'name': '版本', 'values': [{'vid': 'v1', 'name': '12+256G'}]},
            {'name': '颜色分类', 'values': [{'vid': 'c1', 'name': '传奇版'}]},
        ],
        'skus': [{'propPath': 'p:v1;p:c1', 'skuId': 's1'}],
    },
    'sku_core': {'sku2info': {'s1': {'price': {'priceText': '2199'}}}},
}
match = backfill.match_sku(detail, 'iQOO 15', '12+256G', '传奇版')
self.assertEqual(match.price, '2199')
self.assertIsNone(backfill.match_sku(detail, 'iQOO 15', '16+512G', '传奇版'))
```

- [ ] **Step 2: Run the test and verify it fails because the module is missing**

Run:

```powershell
python -m unittest tests.test_iqoo_sku_price_backfill -v
```

Expected: import failure for `src.iqoo_sku_price_backfill`.

- [ ] **Step 3: Implement normalized detail and exact match helpers**

Create `src/iqoo_sku_price_backfill.py` with a `SkuMatch` dataclass,
`normalize_text`, `load_detail_records`, and `match_sku`. Decode
`loader_data_json` to `home.data.res`, map `skuBase.props` and each SKU
`propPath` to visible values, derive SKU price from `skuCore.sku2info`, and
return a match only if the title contains the requested model and all requested
configuration/color text is represented by that SKU's property values.

- [ ] **Step 4: Run matching tests and verify they pass**

Run:

```powershell
python -m unittest tests.test_iqoo_sku_price_backfill -v
```

Expected: all exact-match tests pass.

### Task 2: Add Interest-Free Formatting and Candidate Selection

**Files:**
- Modify: `tests/test_iqoo_sku_price_backfill.py`
- Modify: `src/iqoo_sku_price_backfill.py`

- [ ] **Step 1: Add failing tests for installments and shop candidates**

Add a test that calls `format_installment('2159', 12)` and expects
`¥179.92 × 12期`, while a missing term returns an empty string. Add a temporary
`tmall_shop_items` database with one iQOO 15 title and one unrelated title;
assert `load_shop_candidates` returns only the item whose title contains
`iQOO 15`.

- [ ] **Step 2: Run these tests and verify they fail for missing helpers**

Run:

```powershell
python -m unittest tests.test_iqoo_sku_price_backfill -v
```

Expected: `AttributeError` for installment or candidate helper functions.

- [ ] **Step 3: Implement helpers**

Implement `format_installment` using `Decimal` and `ROUND_HALF_UP`; it returns
an empty string for absent/nonpositive terms or invalid prices. Implement
`extract_installment_terms` to search SKU detail dictionaries recursively for
numeric keys commonly named `installment`, `installmentNum`, `period`, or
`periods`. Implement `load_shop_candidates` to query `tmall_shop_items` by
shop URL and select titles containing the normalized model text.

- [ ] **Step 4: Run the test module and verify it passes**

Run:

```powershell
python -m unittest tests.test_iqoo_sku_price_backfill -v
```

Expected: matching, installment, and candidate-selection tests pass.

### Task 3: Write Workbook and Report Tests

**Files:**
- Modify: `tests/test_iqoo_sku_price_backfill.py`
- Modify: `src/iqoo_sku_price_backfill.py`

- [ ] **Step 1: Add a failing end-to-end workbook test**

Create a temporary workbook with the required eight headers and three rows:
one exact match with installment, one exact match without installment, and one
no-match. Call `write_backfill_workbooks` and assert:

```python
self.assertEqual(filled['G2'].value, '2199')
self.assertEqual(filled['H2'].value, '¥183.25 × 12期')
self.assertEqual(filled['G3'].value, '999')
self.assertIsNone(filled['H3'].value)
self.assertIsNone(filled['G4'].value)
self.assertEqual(report.max_row, 3)
```

- [ ] **Step 2: Run the test and verify it fails because writer functions are missing**

Run:

```powershell
python -m unittest tests.test_iqoo_sku_price_backfill -v
```

Expected: failure naming `write_backfill_workbooks`.

- [ ] **Step 3: Implement workbook output and report generation**

Implement `read_sheet_rows`, `backfill_rows`, and `write_backfill_workbooks`.
Copy the source workbook using `openpyxl.load_workbook`, locate headers by
name, update only `价格` and `免息分期`, and save the requested output path. Use
an independent report workbook with headers `Excel行号`, `机型`, `配置`, `颜色`,
`候选商品ID`, `价格状态`, `免息状态`, and `原因`. Add a report entry for no
candidate, missing exact SKU, missing price, missing installment, or detail
crawl failure.

- [ ] **Step 4: Run tests and verify generated workbooks pass assertions**

Run:

```powershell
python -m unittest tests.test_iqoo_sku_price_backfill -v
```

Expected: all workbook and report tests pass.

### Task 4: Add Controlled Supplementary Crawling and CLI

**Files:**
- Modify: `tests/test_iqoo_sku_price_backfill.py`
- Modify: `src/iqoo_sku_price_backfill.py`

- [ ] **Step 1: Add a failing test for first-error crawl pause**

Inject a fake crawler which fails for the first candidate and tracks calls.
Call `supplement_details` for two models and assert it returns `paused=True`,
records the first candidate error, and the fake crawler was called once.

- [ ] **Step 2: Run the test and verify it fails for the missing supplementary crawler**

Run:

```powershell
python -m unittest tests.test_iqoo_sku_price_backfill -v
```

Expected: failure naming `supplement_details`.

- [ ] **Step 3: Implement supplementary crawl orchestration and CLI**

Implement `supplement_details` to select only candidate IDs from
`load_shop_candidates`, skip successful IDs, invoke `src.taobao_batch.crawl_batch`
for one ID at a time, and stop after its first nonzero result. The CLI defaults
to the two target output paths and accepts source workbook, detail DB, shop DB,
shop URL, and `--no-crawl` options. It prints filled, blank, and report counts.

- [ ] **Step 4: Run tests, compile, and display CLI help**

Run:

```powershell
python -m unittest discover -s tests -v
python -m py_compile src\iqoo_sku_price_backfill.py
python src\iqoo_sku_price_backfill.py --help
```

Expected: all tests pass, compilation exits 0, and help exposes the source,
output, report, SQLite, and `--no-crawl` options.

### Task 5: Run the iQOO Backfill and Verify Output Files

**Files:**
- Input: `target/测试sku表格.xlsx`
- Output: `target/测试sku表格_已填充.xlsx`
- Output: `target/测试sku表格_未匹配报告.xlsx`

- [ ] **Step 1: Run the controlled backfill**

Run:

```powershell
python src\iqoo_sku_price_backfill.py
```

Expected: the command uses successful local details first; if it needs a
candidate from the captured shop list, it delegates one detail request at a
time with the batch crawler's 8–15 second interval and exits supplementary
crawling after a failure.

- [ ] **Step 2: Verify filled and report workbooks independently**

Run a Python verification that confirms the source and filled workbooks have
168 rows, the filled sheet retains the required headers, all nonempty prices
are paired with exact `机型 + 配置 + 颜色` results, and each blank/partial
result has a row in the report workbook.

- [ ] **Step 3: Inspect Git status without staging unrelated changes**

Run:

```powershell
git status --short
```

Expected: report source modifications while retaining the pre-existing move
from `src/tests/taobao_batch.py` to `src/taobao_batch.py` and unrelated
working-tree changes.

## Plan Self-Review

- Spec coverage: Tasks 1–3 implement exact three-field matching, price and
  installment output, preserved source layout, and a report. Task 4 implements
  shop-only supplement crawling with success skipping and first-error pause.
  Task 5 executes and independently checks requested output files.
- Placeholder scan: all implementation steps identify functions, data inputs,
  output paths, and verification commands without unfinished markers.
- Type consistency: `SkuMatch` is produced by `match_sku`, consumed by
  `backfill_rows`, and serialized by `write_backfill_workbooks`; candidate IDs
  flow from `load_shop_candidates` through `supplement_details` to the batch
  crawler.
