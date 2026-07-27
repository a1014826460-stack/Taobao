"""Upload persisted Taobao search main images to the Guonei collection API."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "http://ershou.yunhaixinshi.cn/guonei/api_push.php"


@dataclass(frozen=True)
class UploadResult:
    sent_items: int
    failed_items: int
    batches: int


def _query_values(fingerprint: str) -> tuple[str, str]:
    try:
        value = json.loads(fingerprint)
    except (TypeError, json.JSONDecodeError):
        return "", ""
    return str(value.get("q") or ""), str(value.get("sort") or "")


def build_push_item(row: dict[str, Any]) -> dict[str, Any]:
    """Map a stored item_search row to the documented Guonei push schema."""
    keyword, sort = _query_values(row["query_fingerprint"])
    image_url = str(row.get("pic_url") or "").strip()
    raw_json = row.get("raw_json") or "{}"
    try:
        crawl_result = json.loads(raw_json)
    except (TypeError, json.JSONDecodeError):
        crawl_result = {"raw_json": str(raw_json)}
    return {
        "platform": "淘宝",
        "keyword": keyword,
        "image_type": "首图",
        "sort_type": "销量" if sort in {"_sale", "*bid*"} else "综合",
        "page_num": int(row.get("last_seen_page") or 0),
        "product_url": str(row.get("detail_url") or ""),
        "product_title": str(row.get("title") or ""),
        "image_urls": [image_url],
        "crawl_result": crawl_result,
    }


def load_pending_items(db_path: str | Path, sort: str | None = None) -> list[dict[str, Any]]:
    """Read result items with a main image from the search crawler database."""
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT query_fingerprint, num_iid, title, pic_url, detail_url, last_seen_page, raw_json
            FROM search_items
            WHERE TRIM(COALESCE(pic_url, '')) <> ''
        """
        params: tuple[Any, ...] = ()
        if sort is not None:
            sql += " AND json_extract(query_fingerprint, '$.sort') = ?"
            params = (sort,)
        rows = db.execute(
            sql + """
            ORDER BY query_fingerprint, last_seen_page, num_iid
            """,
            params,
        ).fetchall()
        return [build_push_item(dict(row)) for row in rows]
    finally:
        db.close()


def _chunks(items: list[dict[str, Any]], batch_size: int) -> Iterable[list[dict[str, Any]]]:
    for offset in range(0, len(items), batch_size):
        yield items[offset : offset + batch_size]


def post_json(endpoint: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=timeout) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("Guonei API response is not a JSON object")
    return decoded


def upload_items(
    items: list[dict[str, Any]],
    post_json: Callable[[dict[str, Any]], dict[str, Any]],
    batch_size: int = 100,
) -> UploadResult:
    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    sent = 0
    failed = 0
    batches = 0
    for batch in _chunks(items, batch_size):
        batches += 1
        try:
            result = post_json({"items": batch})
            success_count = int(result.get("success_count", 0))
            failed_count = int(result.get("failed_count", 0))
            if not result.get("success") or success_count + failed_count != len(batch):
                raise ValueError(f"unexpected Guonei API response: {result}")
            sent += success_count
            failed += failed_count
        except Exception:
            failed += len(batch)
    return UploadResult(sent_items=sent, failed_items=failed, batches=batches)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload Taobao item_search main images to Guonei.")
    parser.add_argument("--db", default="data/taobao_search.sqlite3", help="Taobao search SQLite database.")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Guonei push endpoint.")
    parser.add_argument("--batch-size", type=int, default=100, help="Items per JSON POST (default: 100).")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds.")
    parser.add_argument("--sort", default=None, help="Upload only this stored search sort.")
    parser.add_argument("--dry-run", action="store_true", help="Print count only; do not POST.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        items = load_pending_items(args.db, sort=args.sort)
        if args.dry_run:
            print(f"Prepared {len(items)} Guonei image items; no requests sent.")
            return 0
        result = upload_items(
            items,
            post_json=lambda payload: post_json(args.endpoint, payload, args.timeout),
            batch_size=args.batch_size,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        f"Upload finished: batches={result.batches} sent_items={result.sent_items} "
        f"failed_items={result.failed_items}"
    )
    return 0 if result.failed_items == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
