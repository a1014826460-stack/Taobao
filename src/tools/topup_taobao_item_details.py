
"""Top up Taobao item_get details per keyword to a target successful count."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import threading
import time
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import replace
from pathlib import Path
from typing import Any

from src.taobao.direct.item import (
    PROJECT_ROOT,
    ItemCrawlerConfig,
    SQLiteItemStore,
    SearchItemSeed,
    fetch_item_detail,
    parse_item_response,
    utc_now_iso,
    _num_iid_from_search_item,
    _search_items_from_raw_page,
)

DEFAULT_KEYWORDS = [
    "润滑液", "高潮液", "快感液", "延时喷剂", "飞机杯", "电动飞机杯", "男用自慰器", "跳蛋", "穿戴跳蛋",
    "遥控跳蛋", "情趣按摩棒", "震动棒", "AV棒", "吸吮跳蛋", "仿真阳具", "肛塞", "前列腺按摩器", "倒模", "名器",
]
DEFAULT_SORTS = ["", "_sale", "credit", "*bid*", "bid", "bid2", "_bid2", "sale", "_credit", "*sale*", "*bid2*"]
SKIP_STATUSES = {"success", "blocked_5000_pro", "not_found"}


class BillingAuthError(RuntimeError):
    """Raised when Fan-B returns a billing/auth error that must stop all API access."""


def _is_billing_auth_error(error: BaseException | str) -> bool:
    text = str(error)
    return "error_code=4016" in text or "已欠费" in text


def _load_dotenv() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() and name.strip() not in os.environ:
            os.environ[name.strip()] = value.strip().strip("\"'")


def load_candidates(search_db_path: str | Path, keywords: list[str], sorts: list[str]) -> "OrderedDict[str, list[SearchItemSeed]]":
    keyword_filter = set(keywords)
    sort_priority = list(sorts)
    conn = sqlite3.connect(str(search_db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT query_fingerprint, page, raw_json FROM search_pages ORDER BY query_fingerprint, page").fetchall()
    finally:
        conn.close()
    pages_by_keyword_sort: "OrderedDict[str, dict[str, list[sqlite3.Row]]]" = OrderedDict((kw, defaultdict(list)) for kw in keywords)
    for row in rows:
        try:
            fp = json.loads(row["query_fingerprint"])
        except json.JSONDecodeError:
            continue
        kw = str(fp.get("q") or "")
        sort = str(fp.get("sort") or "")
        if kw not in keyword_filter or sort not in sort_priority:
            continue
        pages_by_keyword_sort.setdefault(kw, defaultdict(list))[sort].append(row)
    result: "OrderedDict[str, list[SearchItemSeed]]" = OrderedDict()
    for kw in keywords:
        seen: set[str] = set()
        seeds: list[SearchItemSeed] = []
        pages_by_sort = pages_by_keyword_sort.get(kw, {})
        for sort in sort_priority:
            for row in sorted(pages_by_sort.get(sort, []), key=lambda r: int(r["page"])):
                for search_item in _search_items_from_raw_page(row["raw_json"]):
                    if not isinstance(search_item, dict):
                        continue
                    num_iid = _num_iid_from_search_item(search_item)
                    if not num_iid or num_iid in seen:
                        continue
                    seen.add(num_iid)
                    seeds.append(SearchItemSeed(kw, sort, int(row["page"]), num_iid))
        result[kw] = seeds
    return result


def successful_count(conn: sqlite3.Connection, keyword: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT s.num_iid) AS c
        FROM item_detail_sources s
        JOIN item_detail_state st ON st.num_iid=s.num_iid AND st.status='success'
        JOIN item_details d ON d.num_iid=s.num_iid
        WHERE s.keyword=?
        """,
        (keyword,),
    ).fetchone()
    return int(row["c"] or 0)


def _fetch_and_parse(config: ItemCrawlerConfig, num_iid: str, *, retry_api_errors: bool) -> Any:
    attempts = max(1, int(config.retries)) if retry_api_errors else 1
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            response = fetch_item_detail(config, num_iid)
            parse_item_response(response)
            return response
        except Exception as exc:
            if _is_billing_auth_error(exc):
                raise BillingAuthError(str(exc)) from exc
            last_error = exc
            if "API returned error_code=" not in str(exc):
                break
    assert last_error is not None
    raise last_error


def crawl_one(config: ItemCrawlerConfig, num_iid: str, forced_item_api: str | None = None) -> tuple[str, str, Any]:
    active = replace(config, item_api=forced_item_api) if forced_item_api else config
    try:
        response = _fetch_and_parse(active, num_iid, retry_api_errors=active.item_api != "item_get_pro")
        return num_iid, "success", response
    except Exception as exc:
        if _is_billing_auth_error(exc):
            raise BillingAuthError(str(exc)) from exc
        if active.item_api != "item_get_pro":
            try:
                pro = replace(config, item_api="item_get_pro")
                response = _fetch_and_parse(pro, num_iid, retry_api_errors=True)
                return num_iid, "success", response
            except Exception as pro_exc:
                if _is_billing_auth_error(pro_exc):
                    raise BillingAuthError(str(pro_exc)) from pro_exc
                if "error_code=5000" in str(pro_exc):
                    return num_iid, "blocked_5000_pro", pro_exc
                if "HTTP Error 503" in str(pro_exc) or "503" in str(pro_exc):
                    return num_iid, "abandoned_503", pro_exc
                return num_iid, "error", pro_exc
        if "error_code=5000" in str(exc):
            return num_iid, "blocked_5000_pro", exc
        if "HTTP Error 503" in str(exc) or "503" in str(exc):
            return num_iid, "abandoned_503", exc
        return num_iid, "error", exc


def topup(args: argparse.Namespace) -> int:
    _load_dotenv()
    key = os.environ.get("FANB_API_KEY") or os.environ.get("KEY") or ""
    secret = os.environ.get("FANB_API_SECRET") or os.environ.get("SECRET") or ""
    if not key or not secret:
        raise ValueError("API credentials must be set")
    keywords = args.keyword or DEFAULT_KEYWORDS
    sorts = args.sort or DEFAULT_SORTS
    candidates = load_candidates(args.search_db, keywords, sorts)
    store = SQLiteItemStore(args.db)
    config = ItemCrawlerConfig(
        key=key, secret=secret, num_iids=[], db_path=args.db, max_workers=args.workers,
        lang=args.lang, delay=args.delay, timeout=args.timeout, retries=args.retries, item_api=args.item_api,
    )
    total_fetched = total_failed = total_skipped = 0
    try:
        last_request = 0.0
        throttle_lock = threading.Lock()

        def worker(num_iid: str, forced_api: str | None):
            nonlocal last_request
            with throttle_lock:
                wait_for = last_request + max(0.0, float(args.delay)) - time.monotonic()
                if wait_for > 0:
                    time.sleep(wait_for)
                last_request = time.monotonic()
            return crawl_one(config, num_iid, forced_api)

        for kw, seeds in candidates.items():
            store.save_sources(seeds)
            before = successful_count(store.conn, kw)
            need = max(0, int(args.target) - before)
            if need <= 0:
                print(f"TOPUP keyword={kw} already={before} fetched=0 failed=0 skipped=0")
                continue
            fresh_pending: list[tuple[str, str | None]] = []
            queued_pending: list[tuple[str, str | None]] = []
            retry_error: list[tuple[str, str | None]] = []
            retry_503: list[tuple[str, str | None]] = []
            seen: set[str] = set()
            for seed in seeds:
                if seed.num_iid in seen:
                    continue
                seen.add(seed.num_iid)
                state = store.get_item_state(seed.num_iid)
                status = state.get("status") if state else None
                last_error = str(state.get("last_error") or "") if state else ""
                if "error_code=2000" in last_error or "item-not-found" in last_error:
                    store._upsert_state(seed.num_iid, "not_found", last_error)
                    total_skipped += 1
                    continue
                if _is_billing_auth_error(last_error) and not args.reset:
                    total_skipped += 1
                    continue
                if status in SKIP_STATUSES and not args.reset:
                    total_skipped += 1
                    continue
                forced_api = "item_get_pro" if status == "blocked_5000" else None
                if status is None:
                    fresh_pending.append((seed.num_iid, forced_api))
                elif status == "pending":
                    queued_pending.append((seed.num_iid, forced_api))
                elif status == "abandoned_503":
                    retry_503.append((seed.num_iid, forced_api))
                else:
                    retry_error.append((seed.num_iid, forced_api))
            pending = fresh_pending + queued_pending
            if args.retry_errors:
                pending += retry_error
            if args.retry_503:
                pending += retry_503
            fetched = failed = skipped = 0
            in_flight = set()
            pending_iter = iter(pending)
            with ThreadPoolExecutor(max_workers=int(args.workers)) as executor:
                def submit_until_full():
                    while before + fetched < int(args.target) and len(in_flight) < int(args.workers):
                        try:
                            num_iid, forced_api = next(pending_iter)
                        except StopIteration:
                            break
                        store.mark_pending(num_iid)
                        in_flight.add(executor.submit(worker, num_iid, forced_api))
                submit_until_full()
                while in_flight and before + fetched < int(args.target):
                    done, in_flight = wait(in_flight, return_when=FIRST_COMPLETED)
                    for fut in done:
                        num_iid, status, payload = fut.result()
                        if status == "success":
                            store.save_item_detail(num_iid, payload)
                            fetched += 1
                        elif status == "blocked_5000_pro":
                            store.mark_blocked_5000_pro(num_iid, payload)
                            failed += 1
                        elif status == "abandoned_503":
                            store.mark_abandoned_503(num_iid, payload)
                            failed += 1
                        else:
                            store.mark_error(num_iid, payload)
                            failed += 1
                    submit_until_full()
                # Mark unfinished submitted futures as they complete; they were already requested.
                for fut in in_flight:
                    num_iid, status, payload = fut.result()
                    if status == "success":
                        store.save_item_detail(num_iid, payload)
                        fetched += 1
                    elif status == "blocked_5000_pro":
                        store.mark_blocked_5000_pro(num_iid, payload)
                        failed += 1
                    elif status == "abandoned_503":
                        store.mark_abandoned_503(num_iid, payload)
                        failed += 1
                    else:
                        store.mark_error(num_iid, payload)
                        failed += 1
            after = successful_count(store.conn, kw)
            skipped += max(0, len(seeds) - len(pending))
            total_fetched += fetched
            total_failed += failed
            print(f"TOPUP keyword={kw} before={before} after={after} fetched={fetched} failed={failed} skipped_existing={skipped} candidates={len(seeds)}")
    finally:
        store.close()
    print(f"TOPUP finished fetched={total_fetched} failed={total_failed} skipped_existing={total_skipped}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Top up Taobao item_get details per keyword.")
    p.add_argument("--search-db", default="data/taobao_search.sqlite3")
    p.add_argument("--db", default="data/taobao_item_get.sqlite3")
    p.add_argument("--target", type=int, default=200)
    p.add_argument("--keyword", action="append", default=[])
    p.add_argument("--sort", action="append", default=[])
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--delay", type=float, default=0.15)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--item-api", choices=["item_get", "item_get_pro"], default="item_get")
    p.add_argument("--lang", default="zh-CN")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--retry-errors", action="store_true", help="Retry existing generic error rows after fresh/pending rows.")
    p.add_argument("--retry-503", action="store_true", help="Retry existing abandoned_503 rows after fresh/pending/error rows.")
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        return topup(build_parser().parse_args(argv))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

