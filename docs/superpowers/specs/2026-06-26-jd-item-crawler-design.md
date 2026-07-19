# JD Item Crawler Design

## Goal

Create a standalone lightweight crawler at `src/jd_item_crawler.py` for the Fan-B JD `item_get_pro` API. It reads `key` and `secret` from `password.env`, accepts one or more `num_iid` values, saves promptly to SQLite, and resumes by skipping items already marked `success`.

## Scope

The crawler is separate from the existing Taobao shop and item crawlers. It does not modify the existing `shop_crawler.py` CLI. It focuses on JD item detail retrieval only.

## Command Line

The script supports inline IDs and file-based IDs:

```bash
python src/jd_item_crawler.py --num-iids 10025990353889
python src/jd_item_crawler.py --num-iids 10025990353889,100123456789
python src/jd_item_crawler.py --num-iids-file data/jd_ids.txt
```

Useful options:

- `--env password.env`
- `--db data/jd_item_details.sqlite3`
- `--reset-items`
- `--lang zh-CN`
- `--delay 0.5`
- `--timeout 20`
- `--retries 3`

## Data Model

SQLite contains two tables:

- `jd_item_details`: one row per item, selected common fields plus complete `raw_json`.
- `jd_item_state`: one row per requested `num_iid`, with `pending`, `success`, or `error`, plus `last_error` and timestamps.

The crawler writes state before each request, writes the detail and success state immediately after a valid response, and records errors per item while continuing the batch.

## Resume Behavior

On each run, if a `num_iid` already has `success` state, it is skipped by default. `--reset-items` refetches successful IDs.

## API

The fetcher calls:

```text
https://api-gw.fan-b.com/jd/item_get_pro/
```

with query parameters `key`, `num_iid`, `cache=no`, `lang`, and `secret`.

## Testing

Tests cover input parsing, SQLite upsert and state tracking, resume skipping, error continuation, env config, URL construction, and script help execution.
