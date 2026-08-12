"""Upload Taobao item_get suite images to the Guonei collection API."""

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


def normalize_image_url(url: Any) -> str:
    value = str(url or "").strip()
    if value.startswith("//"):
        return "https:" + value
    return value


def suite_image_urls(raw_item: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    item_imgs = raw_item.get("item_imgs") or []
    if isinstance(item_imgs, dict):
        item_imgs = item_imgs.get("item_img") or item_imgs.get("item") or []
    if isinstance(item_imgs, list):
        for image in item_imgs:
            url = image.get("url") if isinstance(image, dict) else image
            normalized = normalize_image_url(url)
            if normalized and normalized not in seen:
                seen.add(normalized)
                urls.append(normalized)
    if not urls:
        fallback = normalize_image_url(raw_item.get("pic_url"))
        if fallback:
            urls.append(fallback)
    return urls


def _json_or_raw(raw_json: Any) -> dict[str, Any]:
    try:
        payload = json.loads(raw_json or "{}")
    except (TypeError, json.JSONDecodeError):
        return {"raw_json": str(raw_json)}
    return payload if isinstance(payload, dict) else {"raw_json": payload}


def build_detail_push_item(row: dict[str, Any]) -> dict[str, Any]:
    payload = _json_or_raw(row.get("raw_json"))
    raw_item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
    crawl_result = {
        "status": row.get("status") or "success",
        "last_error": row.get("last_error"),
        "source": {"sort": row.get("sort") or "", "page": int(row.get("page") or 0)},
        "detail": payload,
    }
    return {
        "platform": "淘宝",
        "keyword": str(row.get("keyword") or ""),
        "image_type": "套图",
        "sort_type": "综合",
        "page_num": int(row.get("page") or 0),
        "product_url": str(raw_item.get("detail_url") or row.get("detail_url") or f"https://item.taobao.com/item.htm?id={row.get('num_iid') or ''}"),
        "product_title": str(raw_item.get("title") or row.get("title") or ""),
        "image_urls": suite_image_urls(raw_item),
        "crawl_result": crawl_result,
    }


def load_detail_source_items(
    db_path: str | Path,
    *,
    include_failed: bool = True,
    per_keyword_limit: int | None = None,
    updated_since: str | None = None,
    source_created_since: str | None = None,
    target_per_keyword_total: int | None = None,
) -> list[dict[str, Any]]:
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    try:
        status_filter = ""
        if not include_failed:
            status_filter = "AND st.status = 'success'"
        rows = db.execute(
            f"""
            SELECT s.keyword, s.sort, s.page, s.num_iid, s.created_at AS source_created_at,
                   d.title, d.detail_url, d.raw_json, d.updated_at AS detail_updated_at,
                   st.status, st.last_error
            FROM item_detail_sources s
            LEFT JOIN item_details d ON d.num_iid = s.num_iid
            LEFT JOIN item_detail_state st ON st.num_iid = s.num_iid
            WHERE COALESCE(st.status, '') IN ('success', 'blocked_5000', 'error')
            {status_filter}
            ORDER BY s.keyword, s.page, s.sort, s.num_iid
            """
        ).fetchall()
        items: list[dict[str, Any]] = []
        counts_by_keyword: dict[str, int] = {}
        seen_by_keyword: dict[str, set[str]] = {}
        for row in rows:
            row_dict = dict(row)
            keyword = str(row_dict.get("keyword") or "")
            num_iid = str(row_dict.get("num_iid") or "")
            if num_iid in seen_by_keyword.setdefault(keyword, set()):
                continue
            mapped = build_detail_push_item(row_dict)
            if not mapped["image_urls"]:
                continue

            seen_by_keyword[keyword].add(num_iid)
            counts_by_keyword[keyword] = counts_by_keyword.get(keyword, 0) + 1
            current_total = counts_by_keyword[keyword]

            if per_keyword_limit is not None and current_total > per_keyword_limit:
                continue
            if target_per_keyword_total is not None and current_total > target_per_keyword_total:
                continue
            if updated_since or source_created_since:
                detail_updated_at = str(row_dict.get("detail_updated_at") or "")
                source_created_at = str(row_dict.get("source_created_at") or "")
                is_incremental = (updated_since and detail_updated_at >= updated_since) or (
                    source_created_since and source_created_at >= source_created_since
                )
                if not is_incremental:
                    continue
            items.append(mapped)
        return items
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
    parser = argparse.ArgumentParser(description="Upload Taobao item_get suite images to Guonei.")
    parser.add_argument("--db", default="data/taobao_item_get.sqlite3", help="Taobao item_get SQLite database.")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Guonei push endpoint.")
    parser.add_argument("--batch-size", type=int, default=50, help="Items per JSON POST (default: 50).")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds.")
    parser.add_argument("--success-only", action="store_true", help="Only upload successfully fetched item_get rows.")
    parser.add_argument("--per-keyword-limit", type=int, default=None, help="Max unique pushed products per keyword.")
    parser.add_argument("--updated-since", default=None, help="Only upload item_details rows updated at/after this ISO timestamp.")
    parser.add_argument("--source-created-since", default=None, help="Also upload source rows first associated at/after this ISO timestamp.")
    parser.add_argument("--target-per-keyword-total", type=int, default=None, help="When doing incremental upload, only send rows whose per-keyword rank is within this total target.")
    parser.add_argument("--dry-run", action="store_true", help="Print count only; do not POST.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        items = load_detail_source_items(
            args.db,
            include_failed=not args.success_only,
            per_keyword_limit=args.per_keyword_limit,
            updated_since=args.updated_since,
            source_created_since=args.source_created_since,
            target_per_keyword_total=args.target_per_keyword_total,
        )
        if args.dry_run:
            print(f"Prepared {len(items)} Guonei suite-image items; no requests sent.")
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
