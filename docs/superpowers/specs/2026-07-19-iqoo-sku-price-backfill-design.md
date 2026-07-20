# iQOO SKU Price Backfill Design

## Goal

Populate the `价格` and `免息分期` columns in `target/测试sku表格.xlsx` from
locally captured iQOO Tmall product details. Write a separate filled workbook
and a report for every row that cannot be filled exactly.

## Matching Rules

Each worksheet row is matched only when its `机型`, `配置`, and `颜色` values
all exactly match one SKU of a successful item-detail record. No partial title
or nearest-text matching is used when writing values, so a price from a related
but different SKU cannot be applied.

`价格` receives the matched SKU price. `免息分期` receives a string in the form
`¥179.92 × 12期` only when the SKU detail explicitly provides both a price and
an interest-free installment term. If the SKU has no installment information,
the column remains blank even when its price is available.

## Data Sources and Supplementary Crawling

The tool reads successful details from `data/taobao_items.sqlite3`. It reads
candidate item IDs exclusively from `data/taobao_shop_items.sqlite3`, scoped to
the iQOO shop URL. For models with no locally available matching SKU, it selects
only shop-list titles containing the requested model text, then calls the
existing `src/taobao_batch.py` logic one item at a time.

Existing successful detail IDs are skipped. Supplementary crawling uses the
same 8–15 second randomized interval and stops immediately after an HTTP,
captcha, parser, or item-not-found failure. No search outside the captured iQOO
shop list is performed.

## Outputs

- `target/测试sku表格_已填充.xlsx` preserves the source workbook structure and
  writes only the two requested columns.
- `target/测试sku表格_未匹配报告.xlsx` has one row per unfilled or partially
  filled source row. It records the Excel row number, model, configuration,
  color, candidate item IDs, and a precise reason such as `店铺列表未找到机型`,
  `无精确SKU匹配`, `详情爬取失败`, or `未提供免息分期`.

## Verification

Offline tests cover exact SKU matching, no-match reporting, installment
formatting, candidate ID selection, and preservation of untouched cells. The
run verifies that the filled workbook has the original row count, both target
columns exist, every populated price maps to an exact SKU, and every blank or
partial result has a report row.
