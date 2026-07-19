# Item Detail API Design

## Goal

Add a separate Taobao item detail API crawler for `item_get_pro`, while keeping one CLI entry point for both shop search and item detail crawls.

## API Boundary

- Shop search remains in `src/shop_crawler.py` and continues to use `item_search_shop_pro`.
- Item detail crawling is added in `src/item_crawler.py` and uses `item_get_pro`.
- `src/shop_crawler.py` is also the shared CLI entry point. It dispatches to `shop` or `item` commands.

## Item Input

The item command accepts IDs from:

- `--num-iids 520813250866,599262347474`
- `--num-iids-file data/num_iids.txt`

Both sources can be combined. Input supports comma, whitespace, and newline separators. IDs are deduplicated while preserving the first-seen order.

## Persistence and Resume

SQLite remains the storage backend. The item API creates two tables:

- `item_details`: one row per `num_iid`, with common fields and full raw response JSON.
- `item_detail_state`: one row per `num_iid`, with `pending`, `success`, `error`, or `skipped` state.

By default, `item` skips IDs already marked `success`. `--reset-items` forces a re-fetch and overwrites the saved detail row.

## CLI

Examples:

```powershell
python src\shop_crawler.py shop --max-items 100
python src\shop_crawler.py item --num-iids 520813250866,599262347474
python src\shop_crawler.py item --num-iids-file data\num_iids.txt
```

For compatibility, calling without a subcommand still behaves like the shop crawler:

```powershell
python src\shop_crawler.py --max-items 100
```

## Response Shape

The item detail response is parsed from the top-level `item` object, matching the existing `data/sample.json` fixture. The full response is stored in `raw_json`, so missing or future fields do not lose data.
