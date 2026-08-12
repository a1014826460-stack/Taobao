import argparse
import json
import os
import re
import sqlite3
import sys
import threading
import time
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_num_iids(values):
    seen = set()
    result = []
    for value in values or []:
        for part in re.split(r"[\s,]+", str(value).strip()):
            num_iid = part.strip().lstrip("\ufeff")
            if not num_iid or num_iid in seen:
                continue
            seen.add(num_iid)
            result.append(num_iid)
    return result


@dataclass(frozen=True)
class SearchItemSeed:
    keyword: str
    sort: str
    page: int
    num_iid: str


@dataclass
class ItemCrawlerConfig:
    key: str
    secret: str
    num_iids: list[str]
    db_path: str = "data/taobao_shop_items.sqlite3"
    reset_items: bool = False
    max_workers: int = 4
    lang: str = "zh-CN"
    delay: float = 0.5
    timeout: float = 20.0
    retries: int = 3
    item_api: str = "item_get_pro"
    is_promotion: str | None = None
    source_seeds: list[SearchItemSeed] | None = None


@dataclass(frozen=True)
class ItemCrawlResult:
    total: int
    fetched: int
    skipped: int
    failed: int


class SQLiteItemStore:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self):
        self.conn.close()

    def _init_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS item_details (
                num_iid TEXT PRIMARY KEY,
                title TEXT,
                price TEXT,
                orginal_price TEXT,
                nick TEXT,
                detail_url TEXT,
                pic_url TEXT,
                brand TEXT,
                cid TEXT,
                seller_id TEXT,
                shop_id TEXT,
                sales TEXT,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS item_detail_state (
                num_iid TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS item_detail_sources (
                keyword TEXT NOT NULL,
                sort TEXT NOT NULL,
                page INTEGER NOT NULL,
                num_iid TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (keyword, sort, page, num_iid)
            );
            """
        )
        self.conn.commit()

    def get_item_state(self, num_iid):
        row = self.conn.execute(
            "SELECT * FROM item_detail_state WHERE num_iid = ?",
            (str(num_iid),),
        ).fetchone()
        return dict(row) if row else None

    def get_item_detail(self, num_iid):
        row = self.conn.execute(
            "SELECT * FROM item_details WHERE num_iid = ?",
            (str(num_iid),),
        ).fetchone()
        return dict(row) if row else None

    def count_successful(self):
        row = self.conn.execute(
            "SELECT COUNT(*) AS total FROM item_detail_state WHERE status = 'success'"
        ).fetchone()
        return int(row["total"])

    def save_sources(self, seeds: list[SearchItemSeed]) -> None:
        if not seeds:
            return
        now = utc_now_iso()
        with self.conn:
            self.conn.executemany(
                """
                INSERT OR IGNORE INTO item_detail_sources (keyword, sort, page, num_iid, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [(seed.keyword, seed.sort, int(seed.page), seed.num_iid, now) for seed in seeds],
            )

    def mark_pending(self, num_iid):
        self._upsert_state(num_iid, "pending")

    def mark_skipped(self, num_iid):
        self._upsert_state(num_iid, "skipped")

    def mark_error(self, num_iid, error):
        self._upsert_state(num_iid, "error", str(error))

    def mark_blocked_5000(self, num_iid, error):
        self._upsert_state(num_iid, "blocked_5000", str(error))

    def mark_blocked_5000_pro(self, num_iid, error):
        self._upsert_state(num_iid, "blocked_5000_pro", str(error))

    def mark_abandoned_503(self, num_iid, error):
        self._upsert_state(num_iid, "abandoned_503", str(error))

    def save_item_detail(self, num_iid, response):
        now = utc_now_iso()
        item = response.get("item") or {}
        actual_num_iid = str(item.get("num_iid") or num_iid)
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO item_details (
                    num_iid, title, price, orginal_price, nick, detail_url,
                    pic_url, brand, cid, seller_id, shop_id, sales, raw_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(num_iid) DO UPDATE SET
                    title = excluded.title,
                    price = excluded.price,
                    orginal_price = excluded.orginal_price,
                    nick = excluded.nick,
                    detail_url = excluded.detail_url,
                    pic_url = excluded.pic_url,
                    brand = excluded.brand,
                    cid = excluded.cid,
                    seller_id = excluded.seller_id,
                    shop_id = excluded.shop_id,
                    sales = excluded.sales,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                (
                    actual_num_iid,
                    item.get("title"),
                    item.get("price"),
                    item.get("orginal_price"),
                    item.get("nick"),
                    item.get("detail_url"),
                    item.get("pic_url"),
                    item.get("brand"),
                    item.get("cid"),
                    item.get("seller_id"),
                    item.get("shop_id"),
                    None if item.get("sales") is None else str(item.get("sales")),
                    json.dumps(response, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            self._upsert_state(actual_num_iid, "success")

    def _upsert_state(self, num_iid, status, last_error=None):
        now = utc_now_iso()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO item_detail_state (
                    num_iid, status, last_error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(num_iid) DO UPDATE SET
                    status = excluded.status,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (str(num_iid), status, last_error, now, now),
            )


def parse_item_response(response):
    if not isinstance(response, dict):
        raise ValueError("API response is not a JSON object")
    error_code = str(response.get("error_code", ""))
    if error_code and error_code != "0000":
        reason = response.get("reason") or response.get("error") or "API error"
        raise ValueError(f"API returned error_code={error_code}: {reason}")
    item = response.get("item")
    if not isinstance(item, dict):
        raise ValueError("API response missing item object")
    num_iid = str(item.get("num_iid", "")).strip()
    if not num_iid:
        raise ValueError("API item object missing num_iid")
    return item


def crawl_items(config, fetcher=None, store=None):
    if config.max_workers <= 0:
        raise ValueError("max_workers must be a positive integer")
    if config.retries <= 0:
        raise ValueError("retries must be a positive integer")
    if fetcher is None:
        fetcher = fetch_item_detail
    owns_store = store is None
    if store is None:
        store = SQLiteItemStore(config.db_path)

    unique_num_iids = parse_num_iids(config.num_iids)
    fetched = 0
    skipped = 0
    failed = 0
    try:
        if config.source_seeds:
            store.save_sources(config.source_seeds)

        pending: list[tuple[str, str | None]] = []
        for num_iid in unique_num_iids:
            state = store.get_item_state(num_iid)
            status = state.get("status") if state else None
            if status == "blocked_5000" and not config.reset_items:
                store.mark_pending(num_iid)
                pending.append((num_iid, "item_get_pro"))
                continue
            if state and status in {"success", "blocked_5000_pro", "abandoned_503"} and not config.reset_items:
                skipped += 1
                continue
            store.mark_pending(num_iid)
            pending.append((num_iid, None))

        if not pending:
            return ItemCrawlResult(total=len(unique_num_iids), fetched=0, skipped=skipped, failed=0)

        last_request = 0.0
        throttle_lock = threading.Lock()

        def throttled_fetch_once(fetch_config, num_iid):
            nonlocal last_request
            with throttle_lock:
                wait = last_request + max(0.0, float(config.delay)) - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                last_request = time.monotonic()
            return fetcher(fetch_config, num_iid)

        def fetch_with_fallback(num_iid, forced_item_api=None):
            active_config = replace(config, item_api=forced_item_api) if forced_item_api else config
            try:
                response = throttled_fetch_once(active_config, num_iid)
                parse_item_response(response)
                return response
            except Exception:
                if active_config.item_api == "item_get_pro":
                    raise
                pro_config = replace(config, item_api="item_get_pro")
                response = throttled_fetch_once(pro_config, num_iid)
                parse_item_response(response)
                return response

        with ThreadPoolExecutor(max_workers=int(config.max_workers)) as executor:
            future_items = {executor.submit(fetch_with_fallback, num_iid, forced_api): num_iid for num_iid, forced_api in pending}
            for future in as_completed(future_items):
                num_iid = future_items[future]
                try:
                    response = future.result()
                    store.save_item_detail(num_iid, response)
                    fetched += 1
                except Exception as exc:
                    error_text = str(exc)
                    if "error_code=5000" in error_text:
                        if config.item_api == "item_get_pro":
                            store.mark_blocked_5000_pro(num_iid, exc)
                        else:
                            store.mark_blocked_5000_pro(num_iid, exc)
                    elif "HTTP Error 503" in error_text or "503" in error_text:
                        store.mark_abandoned_503(num_iid, exc)
                    else:
                        store.mark_error(num_iid, exc)
                    failed += 1
        return ItemCrawlResult(
            total=len(unique_num_iids),
            fetched=fetched,
            skipped=skipped,
            failed=failed,
        )
    finally:
        if owns_store:
            store.close()


def fetch_item_detail(config, num_iid, opener=urlopen):
    if config.item_api not in {"item_get", "item_get_pro"}:
        raise ValueError("item_api must be 'item_get' or 'item_get_pro'")
    base_url = f"https://api-gw.fan-b.com/taobao/{config.item_api}/"
    params = {
        "key": config.key,
        "num_iid": str(num_iid),
        "lang": config.lang,
        "secret": config.secret,
    }
    if config.item_api == "item_get" and config.is_promotion is not None:
        params["is_promotion"] = str(config.is_promotion)
    url = f"{base_url}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "taobao-item-crawler/1.0"})
    last_error = None

    for attempt in range(1, int(config.retries) + 1):
        try:
            with opener(request, timeout=float(config.timeout)) as response:
                body = response.read().decode("utf-8")
            return json.loads(body)
        except Exception as exc:
            last_error = exc
            if attempt < int(config.retries):
                time.sleep(min(attempt, 5))
    raise RuntimeError(f"request failed after {config.retries} attempt(s): {last_error}")



def _num_iid_from_search_item(search_item: dict[str, Any]) -> str:
    for key in ("num_iid", "item_id", "numIid", "itemId"):
        value = str(search_item.get(key) or "").strip()
        if value:
            return value
    detail_url = str(search_item.get("detail_url") or search_item.get("url") or "")
    match = re.search(r"[?&]id=(\d+)", detail_url)
    return match.group(1) if match else ""


def _search_items_from_raw_page(raw_json: str) -> list[dict[str, Any]]:
    payload = json.loads(raw_json)
    items_node = payload.get("items") if isinstance(payload, dict) else None
    items = items_node.get("item") if isinstance(items_node, dict) else None
    return items if isinstance(items, list) else []


def load_item_ids_from_search(
    search_db_path: str | Path,
    *,
    sort: str = "",
    sorts: list[str] | None = None,
    per_keyword_limit: int = 200,
    keywords: list[str] | None = None,
) -> list[SearchItemSeed]:
    """Load deduplicated item_get seeds from saved item_search pages.

    The limit is applied independently for each keyword after removing duplicate
    商品 ID within that keyword. ``sort`` keeps the original single-sort behavior;
    pass ``sorts`` to use a priority list, e.g. comprehensive first and sales / credit / price as fallback.
    """
    if per_keyword_limit <= 0:
        raise ValueError("per_keyword_limit must be a positive integer")
    sort_priority = list(sorts) if sorts is not None else [sort]
    if not sort_priority:
        raise ValueError("sorts must not be empty")
    keyword_filter = set(keywords or [])
    conn = sqlite3.connect(str(search_db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT query_fingerprint, page, raw_json FROM search_pages ORDER BY query_fingerprint, page"
        ).fetchall()
    finally:
        conn.close()

    pages_by_keyword_sort: "OrderedDict[str, dict[str, list[sqlite3.Row]]]" = OrderedDict()
    for row in rows:
        try:
            fingerprint = json.loads(row["query_fingerprint"])
        except json.JSONDecodeError:
            continue
        keyword = str(fingerprint.get("q") or "")
        page_sort = str(fingerprint.get("sort") or "")
        if page_sort not in sort_priority:
            continue
        if keyword_filter and keyword not in keyword_filter:
            continue
        pages_by_keyword_sort.setdefault(keyword, defaultdict(list))[page_sort].append(row)

    seeds: list[SearchItemSeed] = []
    for keyword, pages_by_sort in pages_by_keyword_sort.items():
        seen_for_keyword: set[str] = set()
        keyword_seeds: list[SearchItemSeed] = []
        for selected_sort in sort_priority:
            for row in sorted(pages_by_sort.get(selected_sort, []), key=lambda item: int(item["page"])):
                for search_item in _search_items_from_raw_page(row["raw_json"]):
                    if not isinstance(search_item, dict):
                        continue
                    num_iid = _num_iid_from_search_item(search_item)
                    if not num_iid or num_iid in seen_for_keyword:
                        continue
                    seen_for_keyword.add(num_iid)
                    keyword_seeds.append(
                        SearchItemSeed(keyword=keyword, sort=selected_sort, page=int(row["page"]), num_iid=num_iid)
                    )
                    if len(keyword_seeds) >= per_keyword_limit:
                        break
                if len(keyword_seeds) >= per_keyword_limit:
                    break
            if len(keyword_seeds) >= per_keyword_limit:
                break
        seeds.extend(keyword_seeds)
    return seeds


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


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Concurrent, resumable Taobao item_get crawler")
    parser.add_argument("ids", nargs="*", help="Optional item IDs; whitespace/comma separated values are accepted.")
    parser.add_argument("--ids-file", action="append", default=[], help="Read item IDs from a UTF-8 text file.")
    parser.add_argument("--from-search-db", default="", help="Load IDs from item_search SQLite pages.")
    parser.add_argument("--search-sort", default="", help="Search sort to load from search_pages (default: comprehensive empty sort).")
    parser.add_argument("--search-sort-fallback", action="append", default=[], help="Additional search sort fallback; repeat to fill each keyword limit across sorts.")
    parser.add_argument("--keyword", action="append", default=[], help="Limit search seeds to one keyword; repeat for multiple.")
    parser.add_argument("--per-keyword-limit", type=int, default=200, help="Max unique item IDs per keyword (default: 200).")
    parser.add_argument("--db", default="data/taobao_item_get.sqlite3", help="Destination SQLite database path.")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent item_get requests (default: 8).")
    parser.add_argument("--delay", type=float, default=0.0, help="Minimum global request interval in seconds.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds.")
    parser.add_argument("--retries", type=int, default=3, help="Attempts per item (default: 3).")
    parser.add_argument("--reset", action="store_true", help="Re-fetch item IDs already saved successfully.")
    parser.add_argument("--item-api", default="item_get", choices=["item_get", "item_get_pro"], help="Fan-B item endpoint (default: item_get).")
    parser.add_argument("--is-promotion", default=None, help="Optional item_get is_promotion parameter.")
    parser.add_argument("--lang", default="zh-CN", help="API language (default: zh-CN).")
    return parser


def _read_id_files(paths: list[str]) -> list[str]:
    values = []
    for path in paths:
        values.append(Path(path).read_text(encoding="utf-8"))
    return values


def config_from_args(args: argparse.Namespace) -> ItemCrawlerConfig:
    _load_dotenv()
    key = os.environ.get("FANB_API_KEY") or os.environ.get("KEY") or ""
    secret = os.environ.get("FANB_API_SECRET") or os.environ.get("SECRET") or ""
    if not key or not secret:
        raise ValueError("API credentials must be set as FANB_API_KEY and FANB_API_SECRET")

    seeds: list[SearchItemSeed] = []
    if args.from_search_db:
        seeds = load_item_ids_from_search(
            args.from_search_db,
            sorts=[args.search_sort, *args.search_sort_fallback],
            per_keyword_limit=args.per_keyword_limit,
            keywords=args.keyword or None,
        )
    explicit_ids = parse_num_iids([*args.ids, *_read_id_files(args.ids_file)])
    seed_ids = [seed.num_iid for seed in seeds]
    num_iids = parse_num_iids([*seed_ids, *explicit_ids])
    if not num_iids:
        raise ValueError("no item IDs to crawl; pass IDs or --from-search-db")
    return ItemCrawlerConfig(
        key=key,
        secret=secret,
        num_iids=num_iids,
        db_path=args.db,
        reset_items=args.reset,
        max_workers=args.workers,
        lang=args.lang,
        delay=args.delay,
        timeout=args.timeout,
        retries=args.retries,
        item_api=args.item_api,
        is_promotion=args.is_promotion,
        source_seeds=seeds,
    )


def main(argv: list[str] | None = None) -> int:
    try:
        config = config_from_args(build_arg_parser().parse_args(argv))
        result = crawl_items(config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        "Item crawl finished: "
        f"total={result.total} fetched={result.fetched} "
        f"skipped={result.skipped} failed={result.failed}"
    )
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
