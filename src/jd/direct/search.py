"""Concurrent, resumable crawler for Fan-B's JD ``item_search`` API.

Run ``python -m src.taobao.direct.search --help`` for command-line options.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SEARCH_API_URL = "https://api-gw.fan-b.com/jd/item_search/"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_int(value: Any, default: int | None = None) -> int | None:
    try:
        return default if value is None or value == "" else int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class JDSearchCrawlerConfig:
    key: str
    secret: str
    query: str
    db_path: str = "data/jd_search.sqlite3"
    max_pages: int = 1
    max_workers: int = 4
    sort: str = "_sale"
    start_price: str = "0"
    end_price: str = "0"
    cat: str = "0"
    discount_only: str = ""
    page_size: str = ""
    seller_info: str = ""
    nick: str = ""
    ppath: str = ""
    imgid: str = ""
    filter: str = ""
    cache: str = "no"
    lang: str = "zh-CN"
    delay: float = 0.0
    timeout: float = 30.0
    retries: int = 3
    reset: bool = False


@dataclass(frozen=True)
class ParsedSearchResponse:
    items: list[dict[str, Any]]
    page: int | None
    page_count: int | None
    total_results: int | None


@dataclass(frozen=True)
class JDSearchCrawlResult:
    requested_pages: int
    fetched_pages: int
    skipped_pages: int
    failed_pages: int
    saved_items: int
    query_fingerprint: str


def query_fingerprint(config: JDSearchCrawlerConfig) -> str:
    """Return a stable identity for a query and its API filters, not its run settings."""
    filters = {
        "q": config.query,
        "sort": config.sort,
        "start_price": config.start_price,
        "end_price": config.end_price,
        "cat": config.cat,
        "discount_only": config.discount_only,
        "page_size": config.page_size,
        "seller_info": config.seller_info,
        "nick": config.nick,
        "ppath": config.ppath,
        "imgid": config.imgid,
        "filter": config.filter,
        "cache": config.cache,
        "lang": config.lang,
    }
    return json.dumps(filters, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


JD_SUPPORTED_SORTS = {"bid", "_bid", "_sale", "_review", "_new"}


def build_search_request(config: JDSearchCrawlerConfig, page: int) -> Request:
    """Build an authenticated item-search request for exactly one result page."""
    if config.sort and config.sort not in JD_SUPPORTED_SORTS:
        raise ValueError("sort must be one of: bid,_bid,_sale,_review,_new")
    params = {
        "key": config.key,
        "q": config.query,
        "start_price": config.start_price,
        "end_price": config.end_price,
        "page": int(page),
        "cat": config.cat,
        "discount_only": config.discount_only,
        "sort": config.sort,
        "page_size": config.page_size,
        "seller_info": config.seller_info,
        "nick": config.nick,
        "ppath": config.ppath,
        "imgid": config.imgid,
        "filter": config.filter,
        "cache": config.cache,
        "lang": config.lang,
        "secret": config.secret,
    }
    return Request(
        f"{SEARCH_API_URL}?{urlencode(params)}",
        headers={"User-Agent": "jd-item-search-crawler/1.0"},
    )


def parse_search_response(response: Any) -> ParsedSearchResponse:
    """Validate the gateway envelope and return the search page fields."""
    if not isinstance(response, dict):
        raise ValueError("API response is not a JSON object")
    error_code = str(response.get("error_code", ""))
    items_node = response.get("items")
    if not isinstance(items_node, dict):
        if error_code and error_code != "0000":
            reason = response.get("reason") or response.get("error") or "API error"
            raise ValueError(f"API returned error_code={error_code}: {reason}")
        raise ValueError("API response missing items object")
    items = items_node.get("item") or []
    if error_code and error_code != "0000" and not items:
        reason = response.get("reason") or response.get("error") or "API error"
        raise ValueError(f"API returned error_code={error_code}: {reason}")
    if not isinstance(items, list):
        raise ValueError("API response items.item is not a list")
    if not all(isinstance(item, dict) for item in items):
        raise ValueError("API response items.item contains a non-object")
    return ParsedSearchResponse(
        items=items,
        page=_to_int(items_node.get("page")),
        page_count=_to_int(items_node.get("page_count")),
        total_results=_to_int(items_node.get("total_results")),
    )


class SQLiteJDSearchStore:
    """Persistence for page snapshots, normalized items, and resumable state."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jd_search_pages (
                query_fingerprint TEXT NOT NULL,
                page INTEGER NOT NULL,
                item_count INTEGER NOT NULL,
                page_count INTEGER,
                total_results INTEGER,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (query_fingerprint, page)
            );
            CREATE TABLE IF NOT EXISTS jd_search_items (
                query_fingerprint TEXT NOT NULL,
                num_iid TEXT NOT NULL,
                title TEXT,
                price TEXT,
                promotion_price TEXT,
                sales TEXT,
                nick TEXT,
                shop_name TEXT,
                detail_url TEXT,
                pic_url TEXT,
                first_seen_page INTEGER NOT NULL,
                last_seen_page INTEGER NOT NULL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (query_fingerprint, num_iid)
            );
            CREATE TABLE IF NOT EXISTS jd_search_state (
                query_fingerprint TEXT NOT NULL,
                page INTEGER NOT NULL,
                status TEXT NOT NULL,
                last_error TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (query_fingerprint, page)
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def get_page_state(self, fingerprint: str, page: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM jd_search_state WHERE query_fingerprint = ? AND page = ?",
            (fingerprint, int(page)),
        ).fetchone()
        return dict(row) if row else None

    def count_pages(self, fingerprint: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS total FROM jd_search_pages WHERE query_fingerprint = ?", (fingerprint,)
        ).fetchone()
        return int(row["total"])

    def count_items(self, fingerprint: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS total FROM jd_search_items WHERE query_fingerprint = ?", (fingerprint,)
        ).fetchone()
        return int(row["total"])

    def get_item(self, fingerprint: str, num_iid: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM jd_search_items WHERE query_fingerprint = ? AND num_iid = ?",
            (fingerprint, str(num_iid)),
        ).fetchone()
        return dict(row) if row else None

    def mark_error(self, fingerprint: str, page: int, error: Exception) -> None:
        now = utc_now_iso()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO jd_search_state (query_fingerprint, page, status, last_error, updated_at)
                VALUES (?, ?, 'error', ?, ?)
                ON CONFLICT(query_fingerprint, page) DO UPDATE SET
                    status = excluded.status, last_error = excluded.last_error, updated_at = excluded.updated_at
                """,
                (fingerprint, int(page), str(error), now),
            )

    def save_page(self, fingerprint: str, page: int, response: dict[str, Any]) -> None:
        parsed = parse_search_response(response)
        now = utc_now_iso()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO jd_search_pages (
                    query_fingerprint, page, item_count, page_count, total_results, raw_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(query_fingerprint, page) DO UPDATE SET
                    item_count = excluded.item_count, page_count = excluded.page_count,
                    total_results = excluded.total_results, raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                (
                    fingerprint, int(page), len(parsed.items), parsed.page_count, parsed.total_results,
                    json.dumps(response, ensure_ascii=False), now, now,
                ),
            )
            for item in parsed.items:
                num_iid = str(item.get("num_iid") or item.get("item_id") or "").strip()
                if not num_iid:
                    continue
                self.conn.execute(
                    """
                    INSERT INTO jd_search_items (
                        query_fingerprint, num_iid, title, price, promotion_price, sales, nick, shop_name,
                        detail_url, pic_url, first_seen_page, last_seen_page, raw_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(query_fingerprint, num_iid) DO UPDATE SET
                        title = excluded.title, price = excluded.price,
                        promotion_price = excluded.promotion_price, sales = excluded.sales,
                        nick = excluded.nick, shop_name = excluded.shop_name,
                        detail_url = excluded.detail_url, pic_url = excluded.pic_url,
                        last_seen_page = excluded.last_seen_page, raw_json = excluded.raw_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        fingerprint, num_iid, item.get("title"), item.get("price"),
                        item.get("promotion_price"),
                        None if item.get("sales") is None else str(item.get("sales")),
                        item.get("nick"), item.get("shop_name"), item.get("detail_url"), item.get("pic_url"),
                        int(page), int(page), json.dumps(item, ensure_ascii=False), now, now,
                    ),
                )
            self.conn.execute(
                """
                INSERT INTO jd_search_state (query_fingerprint, page, status, last_error, updated_at)
                VALUES (?, ?, 'success', NULL, ?)
                ON CONFLICT(query_fingerprint, page) DO UPDATE SET
                    status = excluded.status, last_error = NULL, updated_at = excluded.updated_at
                """,
                (fingerprint, int(page), now),
            )


def fetch_search_page(config: JDSearchCrawlerConfig, page: int, opener=urlopen) -> dict[str, Any]:
    """Request one page and retry both transport failures and API error envelopes."""
    request = build_search_request(config, page)
    last_error: Exception | None = None
    for attempt in range(1, int(config.retries) + 1):
        try:
            with opener(request, timeout=float(config.timeout)) as response:
                payload = json.loads(response.read().decode("utf-8"))
            parse_search_response(payload)
            return payload
        except Exception as exc:
            last_error = exc
            if attempt < int(config.retries):
                time.sleep(min(attempt, 5))
    raise RuntimeError(f"request failed after {config.retries} attempt(s): {last_error}")


def crawl_search(
    config: JDSearchCrawlerConfig,
    fetcher: Callable[[JDSearchCrawlerConfig, int], dict[str, Any]] | None = None,
) -> JDSearchCrawlResult:
    """Crawl pages 1..max_pages concurrently and persist each completed response."""
    if not config.query.strip():
        raise ValueError("query must not be empty")
    if config.max_pages <= 0:
        raise ValueError("max_pages must be a positive integer")
    if config.max_workers <= 0:
        raise ValueError("max_workers must be a positive integer")
    if config.retries <= 0:
        raise ValueError("retries must be a positive integer")

    fingerprint = query_fingerprint(config)
    store = SQLiteJDSearchStore(config.db_path)
    try:
        pages = list(range(1, int(config.max_pages) + 1))
        pending = pages if config.reset else [
            page for page in pages
            if (state := store.get_page_state(fingerprint, page)) is None or state["status"] != "success"
        ]
        skipped = len(pages) - len(pending)
        fetched = 0
        failed = 0

        if fetcher is None:
            last_request = 0.0
            throttle_lock = threading.Lock()

            def default_fetcher(crawler_config: JDSearchCrawlerConfig, page: int) -> dict[str, Any]:
                nonlocal last_request
                with throttle_lock:
                    wait = last_request + max(0.0, float(crawler_config.delay)) - time.monotonic()
                    if wait > 0:
                        time.sleep(wait)
                    last_request = time.monotonic()
                return fetch_search_page(crawler_config, page)

            active_fetcher = default_fetcher
        else:
            active_fetcher = fetcher

        with ThreadPoolExecutor(max_workers=int(config.max_workers)) as executor:
            future_pages = {executor.submit(active_fetcher, config, page): page for page in pending}
            for future in as_completed(future_pages):
                page = future_pages[future]
                try:
                    response = future.result()
                    store.save_page(fingerprint, page, response)
                    fetched += 1
                except Exception as exc:
                    store.mark_error(fingerprint, page, exc)
                    failed += 1
        return JDSearchCrawlResult(
            requested_pages=len(pages),
            fetched_pages=fetched,
            skipped_pages=skipped,
            failed_pages=failed,
            saved_items=store.count_items(fingerprint),
            query_fingerprint=fingerprint,
        )
    finally:
        store.close()


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
    parser = argparse.ArgumentParser(description="Concurrent, resumable JD item_search crawler")
    parser.add_argument("--q", required=True, help="JD search keyword.")
    parser.add_argument("--max-pages", type=int, default=1, help="Pages 1 through this limit (default: 1).")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent requests (default: 4).")
    parser.add_argument("--db", default="data/jd_search.sqlite3", help="SQLite database path.")
    parser.add_argument("--sort", default="_sale", help="JD search sort: bid,_bid,_sale,_review,_new (default: _sale).")
    parser.add_argument("--start-price", default="0", help="Minimum price (default: 0).")
    parser.add_argument("--end-price", default="0", help="Maximum price (default: 0).")
    parser.add_argument("--cat", default="0", help="Taobao category ID (default: 0).")
    parser.add_argument("--discount-only", default="", help="API discount_only value.")
    parser.add_argument("--page-size", default="", help="API page_size value.")
    parser.add_argument("--seller-info", default="", help="API seller_info value.")
    parser.add_argument("--nick", default="", help="API nick value.")
    parser.add_argument("--ppath", default="", help="API ppath value.")
    parser.add_argument("--imgid", default="", help="API imgid value.")
    parser.add_argument("--filter", default="", help="API filter value.")
    parser.add_argument("--cache", default="no", help="API cache value (default: no).")
    parser.add_argument("--lang", default="zh-CN", help="API language (default: zh-CN).")
    parser.add_argument("--delay", type=float, default=0.0, help="Minimum global request interval in seconds.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds.")
    parser.add_argument("--retries", type=int, default=3, help="Attempts per page (default: 3).")
    parser.add_argument("--reset", action="store_true", help="Re-fetch pages already saved successfully.")
    return parser


def config_from_args(args: argparse.Namespace) -> JDSearchCrawlerConfig:
    _load_dotenv()
    key = os.environ.get("FANB_API_KEY") or os.environ.get("KEY") or ""
    secret = os.environ.get("FANB_API_SECRET") or os.environ.get("SECRET") or ""
    if not key or not secret:
        raise ValueError("API credentials must be set as FANB_API_KEY and FANB_API_SECRET")
    return JDSearchCrawlerConfig(
        key=key, secret=secret, query=args.q, db_path=args.db, max_pages=args.max_pages,
        max_workers=args.workers, sort=args.sort, start_price=args.start_price,
        end_price=args.end_price, cat=args.cat, discount_only=args.discount_only,
        page_size=args.page_size, seller_info=args.seller_info, nick=args.nick,
        ppath=args.ppath, imgid=args.imgid, filter=args.filter, cache=args.cache,
        lang=args.lang, delay=args.delay, timeout=args.timeout, retries=args.retries, reset=args.reset,
    )


def main(argv: list[str] | None = None) -> int:
    try:
        config = config_from_args(build_arg_parser().parse_args(argv))
        result = crawl_search(config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        "JD search crawl finished: "
        f"requested_pages={result.requested_pages} fetched_pages={result.fetched_pages} "
        f"skipped_pages={result.skipped_pages} failed_pages={result.failed_pages} "
        f"saved_items={result.saved_items}"
    )
    return 0 if result.failed_pages == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

