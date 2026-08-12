"""Upload persisted JD search and detail image data to the Guonei collection API.

This script only reads local SQLite databases and posts to the Guonei upload API.
It does not call Fan-B APIs.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "http://ershou.yunhaixinshi.cn/guonei/api_push.php"
DEFAULT_SEARCH_DB = "data/jd_search.sqlite3"
DEFAULT_DETAIL_DB = "data/jd_item_details.sqlite3"
DEFAULT_STATE_DB = "data/guonei_upload_state.sqlite3"


@dataclass(frozen=True)
class PendingItem:
    key: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class UploadResult:
    sent_items: int
    failed_items: int
    batches: int


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_image_url(url: Any) -> str:
    value = str(url or "").strip()
    if value.startswith("//"):
        return "https:" + value
    return value


def _json_or_raw(raw_json: Any) -> dict[str, Any]:
    try:
        payload = json.loads(raw_json or "{}")
    except (TypeError, json.JSONDecodeError):
        return {"raw_json": str(raw_json)}
    return payload if isinstance(payload, dict) else {"raw_json": payload}


def _query_values(fingerprint: str) -> tuple[str, str]:
    try:
        value = json.loads(fingerprint or "{}")
    except (TypeError, json.JSONDecodeError):
        return "", ""
    return str(value.get("q") or ""), str(value.get("sort") or "")


def sort_type_label(sort: Any) -> str:
    """Map stored sort values to Guonei API allowed values: 销量 or 综合."""
    value = str(sort or "")
    sales_values = {"_sale", "sale", "*sale*", "*bid*", "bid", "bid2", "_bid2", "*bid2*"}
    return "销量" if value in sales_values else "综合"


def make_key(kind: str, keyword: Any, sort: Any, page: Any, num_iid: Any) -> str:
    return f"{kind}:{str(keyword or '')}:{str(sort or '')}:{int(page or 0)}:{str(num_iid or '')}"


def init_upload_state(state_db: str | Path) -> None:
    db_path = Path(state_db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS guonei_upload_state (
                upload_key TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                uploaded_at TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                response_json TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def successful_keys(state_db: str | Path) -> set[str]:
    init_upload_state(state_db)
    conn = sqlite3.connect(str(state_db))
    try:
        return {row[0] for row in conn.execute("SELECT upload_key FROM guonei_upload_state WHERE status = 'success'")}
    finally:
        conn.close()


def mark_uploaded(state_db: str | Path, keys: list[str], response: dict[str, Any] | None = None) -> None:
    if not keys:
        return
    init_upload_state(state_db)
    ts = now_iso()
    response_json = json.dumps(response or {}, ensure_ascii=False)
    conn = sqlite3.connect(str(state_db))
    try:
        conn.executemany(
            """
            INSERT INTO guonei_upload_state(upload_key, status, uploaded_at, attempts, last_error, response_json)
            VALUES (?, 'success', ?, 1, NULL, ?)
            ON CONFLICT(upload_key) DO UPDATE SET
                status='success',
                uploaded_at=excluded.uploaded_at,
                attempts=guonei_upload_state.attempts + 1,
                last_error=NULL,
                response_json=excluded.response_json
            """,
            [(key, ts, response_json) for key in keys],
        )
        conn.commit()
    finally:
        conn.close()


def mark_failed(state_db: str | Path, keys: list[str], error: str, response: dict[str, Any] | None = None) -> None:
    if not keys:
        return
    init_upload_state(state_db)
    response_json = json.dumps(response or {}, ensure_ascii=False)
    conn = sqlite3.connect(str(state_db))
    try:
        conn.executemany(
            """
            INSERT INTO guonei_upload_state(upload_key, status, uploaded_at, attempts, last_error, response_json)
            VALUES (?, 'error', NULL, 1, ?, ?)
            ON CONFLICT(upload_key) DO UPDATE SET
                status='error',
                attempts=guonei_upload_state.attempts + 1,
                last_error=excluded.last_error,
                response_json=excluded.response_json
            """,
            [(key, error[:4000], response_json) for key in keys],
        )
        conn.commit()
    finally:
        conn.close()


def build_search_push_item(row: dict[str, Any]) -> dict[str, Any]:
    keyword, sort = _query_values(str(row.get("query_fingerprint") or ""))
    image_url = normalize_image_url(row.get("pic_url"))
    return {
        "platform": "京东",
        "keyword": keyword,
        "image_type": "首图",
        "sort_type": sort_type_label(sort),
        "page_num": int(row.get("last_seen_page") or row.get("first_seen_page") or 0),
        "product_url": str(row.get("detail_url") or ""),
        "product_title": str(row.get("title") or ""),
        "image_urls": [image_url] if image_url else [],
        "crawl_result": _json_or_raw(row.get("raw_json")),
    }


def _extract_urls_from_image_collection(collection: Any) -> list[str]:
    if isinstance(collection, dict):
        for key in ("item_img", "item", "images", "image", "list"):
            if key in collection:
                collection = collection.get(key)
                break
    if not isinstance(collection, list):
        collection = [collection] if collection else []

    urls: list[str] = []
    seen: set[str] = set()
    for image in collection:
        if isinstance(image, dict):
            url = image.get("url") or image.get("pic_url") or image.get("image_url") or image.get("src")
        else:
            url = image
        normalized = normalize_image_url(url)
        if normalized and normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)
    return urls


def detail_image_urls(raw_item: dict[str, Any]) -> list[str]:
    """Return JD product suite images, preferring item_images and supporting stored item_imgs."""
    for key in ("item_images", "item_imgs"):
        urls = _extract_urls_from_image_collection(raw_item.get(key))
        if urls:
            return urls
    fallback = normalize_image_url(raw_item.get("pic_url"))
    return [fallback] if fallback else []


def build_detail_push_item(row: dict[str, Any]) -> dict[str, Any]:
    payload = _json_or_raw(row.get("raw_json"))
    raw_item = payload.get("item") if isinstance(payload.get("item"), dict) else payload
    if not isinstance(raw_item, dict):
        raw_item = {}
    sort = row.get("sort") or ""
    crawl_result = {
        "status": row.get("status") or "success",
        "last_error": row.get("last_error"),
        "source": {"sort": str(sort), "page": int(row.get("page") or 0)},
        "detail": payload,
    }
    return {
        "platform": "京东",
        "keyword": str(row.get("keyword") or ""),
        "image_type": "套图",
        "sort_type": sort_type_label(sort),
        "page_num": int(row.get("page") or 0),
        "product_url": str(raw_item.get("detail_url") or row.get("detail_url") or f"https://item.jd.com/{row.get('num_iid') or ''}.html"),
        "product_title": str(raw_item.get("title") or row.get("title") or ""),
        "image_urls": detail_image_urls(raw_item),
        "crawl_result": crawl_result,
    }


def load_pending_search_items(
    search_db: str | Path,
    state_db: str | Path,
    *,
    keyword: str | None = None,
    sort: str | None = None,
    limit: int | None = None,
) -> list[PendingItem]:
    done = successful_keys(state_db)
    conn = sqlite3.connect(str(search_db))
    conn.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT query_fingerprint, num_iid, title, detail_url, pic_url,
                   first_seen_page, last_seen_page, raw_json
            FROM jd_search_items
            WHERE TRIM(COALESCE(pic_url, '')) <> ''
        """
        params: list[Any] = []
        if keyword is not None:
            sql += " AND json_extract(query_fingerprint, '$.q') = ?"
            params.append(keyword)
        if sort is not None:
            sql += " AND json_extract(query_fingerprint, '$.sort') = ?"
            params.append(sort)
        sql += " ORDER BY json_extract(query_fingerprint, '$.q'), json_extract(query_fingerprint, '$.sort'), last_seen_page, num_iid"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    pending: list[PendingItem] = []
    for row in rows:
        row_dict = dict(row)
        kw, st = _query_values(str(row_dict.get("query_fingerprint") or ""))
        page = int(row_dict.get("last_seen_page") or row_dict.get("first_seen_page") or 0)
        key = make_key("jd_search", kw, st, page, row_dict.get("num_iid"))
        if key in done:
            continue
        payload = build_search_push_item(row_dict)
        if not payload["keyword"] or not payload["image_urls"]:
            continue
        pending.append(PendingItem(key=key, payload=payload))
        if limit is not None and len(pending) >= limit:
            break
    return pending


def load_pending_detail_items(
    detail_db: str | Path,
    state_db: str | Path,
    *,
    keyword: str | None = None,
    sort: str | None = None,
    limit: int | None = None,
) -> list[PendingItem]:
    done = successful_keys(state_db)
    conn = sqlite3.connect(str(detail_db))
    conn.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT s.keyword, s.sort, s.page, s.num_iid, s.created_at AS source_created_at,
                   d.title, d.detail_url, d.pic_url, d.raw_json, d.updated_at AS detail_updated_at,
                   st.status, st.last_error
            FROM jd_item_sources s
            JOIN jd_item_details d ON d.num_iid = s.num_iid
            JOIN jd_item_state st ON st.num_iid = s.num_iid
            WHERE st.status = 'success'
              AND TRIM(COALESCE(d.raw_json, '')) <> ''
        """
        params: list[Any] = []
        if keyword is not None:
            sql += " AND s.keyword = ?"
            params.append(keyword)
        if sort is not None:
            sql += " AND s.sort = ?"
            params.append(sort)
        sql += " ORDER BY s.keyword, s.sort, s.page, s.num_iid"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    pending: list[PendingItem] = []
    for row in rows:
        row_dict = dict(row)
        key = make_key("jd_detail", row_dict.get("keyword"), row_dict.get("sort"), row_dict.get("page"), row_dict.get("num_iid"))
        if key in done:
            continue
        payload = build_detail_push_item(row_dict)
        if not payload["keyword"] or not payload["image_urls"]:
            continue
        pending.append(PendingItem(key=key, payload=payload))
        if limit is not None and len(pending) >= limit:
            break
    return pending


def _chunks(items: list[PendingItem], batch_size: int) -> Iterable[list[PendingItem]]:
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
    items: list[PendingItem],
    *,
    state_db: str | Path,
    post_json_func: Callable[[dict[str, Any]], dict[str, Any]],
    batch_size: int = 50,
    max_failed_batches: int = 3,
) -> UploadResult:
    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    sent = 0
    failed = 0
    batches = 0
    consecutive_failed_batches = 0
    for batch in _chunks(items, batch_size):
        batches += 1
        keys = [item.key for item in batch]
        payload = {"items": [item.payload for item in batch]}
        try:
            result = post_json_func(payload)
            success_count = int(result.get("success_count", 0))
            failed_count = int(result.get("failed_count", 0))
            results = result.get("results")
            if success_count + failed_count != len(batch):
                raise ValueError(f"unexpected Guonei API response: {result}")
            if isinstance(results, list) and len(results) == len(batch):
                success_keys = [key for key, row_result in zip(keys, results) if isinstance(row_result, dict) and row_result.get("success")]
                failed_keys = [key for key, row_result in zip(keys, results) if not (isinstance(row_result, dict) and row_result.get("success"))]
                mark_uploaded(state_db, success_keys, result)
                if failed_keys:
                    mark_failed(state_db, failed_keys, "item-level failure", result)
                sent += len(success_keys)
                failed += len(failed_keys)
                consecutive_failed_batches = consecutive_failed_batches + 1 if failed_keys and not success_keys else 0
            else:
                if failed_count == 0 and success_count == len(batch):
                    mark_uploaded(state_db, keys, result)
                    sent += len(batch)
                    consecutive_failed_batches = 0
                else:
                    mark_failed(state_db, keys, "partial batch failure without per-item results", result)
                    sent += success_count
                    failed += failed_count
                    consecutive_failed_batches += 1
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            mark_failed(state_db, keys, str(exc))
            failed += len(batch)
            consecutive_failed_batches += 1
            print(f"Batch {batches} failed: {exc}", file=sys.stderr)
        if max_failed_batches > 0 and consecutive_failed_batches >= max_failed_batches:
            print(f"Stopping after {consecutive_failed_batches} consecutive failed batches.", file=sys.stderr)
            break
    return UploadResult(sent_items=sent, failed_items=failed, batches=batches)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload JD search/detail images to Guonei.")
    parser.add_argument("--search-db", default=DEFAULT_SEARCH_DB, help="JD search SQLite database.")
    parser.add_argument("--detail-db", default=DEFAULT_DETAIL_DB, help="JD item detail SQLite database.")
    parser.add_argument("--state-db", default=DEFAULT_STATE_DB, help="Local upload state SQLite database.")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Guonei push endpoint.")
    parser.add_argument("--kind", choices=["search", "detail", "all"], default="all", help="Which JD data to upload.")
    parser.add_argument("--keyword", default=None, help="Upload only one keyword.")
    parser.add_argument("--sort", default=None, help="Upload only one stored sort value.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum pending items per selected kind.")
    parser.add_argument("--batch-size", type=int, default=50, help="Items per JSON POST (default: 50).")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds.")
    parser.add_argument("--max-failed-batches", type=int, default=3, help="Stop after this many consecutive failed batches (default: 3; 0 disables).")
    parser.add_argument("--dry-run", action="store_true", help="Print counts and examples; do not POST.")
    parser.add_argument("--sample-size", type=int, default=2, help="Number of sample payloads to print during dry-run.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        init_upload_state(args.state_db)
        pending: list[PendingItem] = []
        if args.kind in {"search", "all"}:
            search_items = load_pending_search_items(args.search_db, args.state_db, keyword=args.keyword, sort=args.sort, limit=args.limit)
            print(f"Prepared JD search items: {len(search_items)}")
            pending.extend(search_items)
        if args.kind in {"detail", "all"}:
            detail_items = load_pending_detail_items(args.detail_db, args.state_db, keyword=args.keyword, sort=args.sort, limit=args.limit)
            print(f"Prepared JD detail items: {len(detail_items)}")
            pending.extend(detail_items)

        if args.dry_run:
            print(f"Dry-run total pending: {len(pending)}; no requests sent.")
            for item in pending[: max(0, args.sample_size)]:
                print("UPLOAD_KEY", item.key)
                sample = dict(item.payload)
                print(json.dumps(sample, ensure_ascii=False, indent=2)[:3000])
            return 0

        result = upload_items(
            pending,
            state_db=args.state_db,
            post_json_func=lambda payload: post_json(args.endpoint, payload, args.timeout),
            batch_size=args.batch_size,
            max_failed_batches=args.max_failed_batches,
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
