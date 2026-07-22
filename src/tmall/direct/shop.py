"""Fetch a selected range of Tmall shop search pages into SQLite."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import time
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit, urlunsplit


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class CrawlerConfig:
    shop_url: str
    start_page: int
    pages: int | None
    db_path: Path
    timeout: float
    cookies: dict[str, str]


def parse_cookie_header(value: str) -> dict[str, str]:
    """Convert a Cookie request header into requests' cookie mapping."""
    cookies: dict[str, str] = {}
    for part in value.split(";"):
        name, separator, cookie_value = part.strip().partition("=")
        if separator and name:
            cookies[name] = cookie_value
    return cookies


def build_page_request(shop_url: str, page_number: int) -> tuple[str, dict[str, str], dict[str, str]]:
    """Derive the Tmall async search request from a shop search URL."""
    parsed = urlsplit(shop_url)
    hostname = parsed.hostname.lower() if parsed.hostname else ""
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or (hostname != "tmall.com" and not hostname.endswith(".tmall.com"))
    ):
        raise ValueError("shop_url must be an http(s) Tmall shop URL")
    if page_number <= 0:
        raise ValueError("page_number must be positive")

    query = parse_qs(parsed.query, keep_blank_values=True)
    request_url = urlunsplit((parsed.scheme, parsed.netloc, "/i/asynSearch.htm", "", ""))
    params = {
        "path": "/search.htm",
        "search": "y",
        "orderType": query.get("orderType", ["defaultSort"])[0],
        "viewType": query.get("viewType", ["grid"])[0],
        "keyword": query.get("keyword", [""])[0],
        "lowPrice": query.get("lowPrice", [""])[0],
        "highPrice": query.get("highPrice", [""])[0],
        "pageNo": str(page_number),
        "callback": "jsonp91",
    }
    # Tmall's legacy endpoint expects these widget identifiers on live requests.
    params["_ksTS"] = f"{int(time.time() * 1000)}_{page_number}"
    params["mid"] = "w-14962063618-0"
    params["wid"] = "14962063618"
    headers = {
        "Accept": "application/javascript, text/javascript, */*; q=0.01",
        "Referer": shop_url,
        "User-Agent": USER_AGENT,
        "X-Requested-With": "XMLHttpRequest",
    }
    return request_url, params, headers


def decode_payload(text: str) -> dict[str, Any] | str:
    """Decode a JSON body or one JSONP callback wrapper."""
    body = text.strip()
    if not body:
        raise ValueError("response body is empty")
    if body.startswith("{"):
        payload = json.loads(body)
    else:
        opening = body.find("(")
        if opening <= 0 or not body.endswith(")") and not body.endswith(");"):
            raise ValueError("response is neither JSON nor JSONP")
        json_text = body[opening + 1 :].rstrip().rstrip(";").rstrip()
        if not json_text.endswith(")"):
            raise ValueError("JSONP response is missing closing parenthesis")
        # Legacy Tmall responses can embed raw control characters in the
        # JSONP string payload, which Python accepts in non-strict mode.
        payload = json.loads(json_text[:-1], strict=False)
    if not isinstance(payload, (dict, str)):
        raise ValueError("response payload is neither a JSON object nor an HTML string")
    return payload


def _nested_value(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first_value(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def extract_products(payload: dict[str, Any] | str, page_number: int) -> list[dict[str, Any]]:
    """Locate a Tmall product list and normalize the common fields."""
    if isinstance(payload, str):
        return _extract_products_from_html(payload, page_number)
    candidates = (
        ("itemList",),
        ("data", "itemList"),
        ("itemDOList",),
        ("data", "itemDOList"),
        ("mods", "itemList", "data", "auctions"),
        ("mods", "itemList", "data", "items"),
    )
    raw_items = next(
        (value for path in candidates if isinstance((value := _nested_value(payload, path)), list)),
        None,
    )
    if raw_items is None:
        raise ValueError("response payload does not contain a product list")

    products: list[dict[str, Any]] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise ValueError("product list contains a non-object item")
        item_id = _first_value(raw_item, "item_id", "itemId", "nid", "id")
        if not item_id:
            raise ValueError("product item is missing an ID")
        products.append(
            {
                "item_id": item_id,
                "title": _first_value(raw_item, "title", "raw_title", "itemTitle"),
                "price": _first_value(raw_item, "price", "view_price", "priceText"),
                "original_price": _first_value(raw_item, "original_price", "reserve_price", "originalPrice"),
                "item_url": _first_value(raw_item, "detail_url", "item_url", "detailUrl", "url"),
                "image_url": _first_value(raw_item, "pic_url", "picUrl", "image", "image_url"),
                "sales": _first_value(raw_item, "sales", "view_sales", "sellCount", "sellCountText"),
                "page_number": page_number,
                "raw_item": raw_item,
            }
        )
    return products


def _clean_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def _html_attribute(tag: str, name: str) -> str:
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        tag,
        re.IGNORECASE | re.DOTALL,
    )
    return match.group(2).strip() if match else ""


def _extract_products_from_html(html: str, page_number: int) -> list[dict[str, Any]]:
    """Parse legacy Tmall asynchronous-search HTML rows without dependencies."""
    row_pattern = re.compile(
        r'<dl\b[^>]*\bdata-id\s*=\s*(["\'])(?P<item_id>[^"\']+)\1[^>]*>(?P<body>.*?)</dl>',
        re.IGNORECASE | re.DOTALL,
    )
    products: list[dict[str, Any]] = []
    for match in row_pattern.finditer(html):
        item_id = match.group("item_id").strip()
        body = match.group("body")
        link_match = re.search(
            r'<a\b[^>]*\bhref\s*=\s*(["\'])(?P<href>.*?)\1',
            body,
            re.IGNORECASE | re.DOTALL,
        )
        image_match = re.search(r'<img\b(?P<tag>[^>]*)>', body, re.IGNORECASE | re.DOTALL)
        title_match = re.search(
            r'<div\b[^>]*\bclass\s*=\s*(["\'])[^"\']*\bdetail\b[^"\']*\1[^>]*>(?P<title>.*?)</div>',
            body,
            re.IGNORECASE | re.DOTALL,
        )
        price_match = re.search(
            r'<(?:span|em)\b[^>]*\bclass\s*=\s*(["\'])[^"\']*\bc-price\b[^"\']*\1[^>]*>(?P<price>.*?)</(?:span|em)>',
            body,
            re.IGNORECASE | re.DOTALL,
        )
        sales_match = re.search(
            r'<(?:span|div)\b[^>]*\bclass\s*=\s*(["\'])[^"\']*\bsale-num\b[^"\']*\1[^>]*>(?P<sales>.*?)</(?:span|div)>',
            body,
            re.IGNORECASE | re.DOTALL,
        )
        href = link_match.group("href").strip() if link_match else ""
        if href.startswith("//"):
            href = "https:" + href
        image_tag = image_match.group("tag") if image_match else ""
        image_url = _html_attribute(image_tag, "data-ks-lazyload") or _html_attribute(image_tag, "src")
        if image_url.startswith("//"):
            image_url = "https:" + image_url
        products.append(
            {
                "item_id": item_id,
                "title": _clean_html(title_match.group("title")) if title_match else "",
                "price": _clean_html(price_match.group("price")) if price_match else "",
                "original_price": "",
                "item_url": href,
                "image_url": image_url,
                "sales": _clean_html(sales_match.group("sales")) if sales_match else "",
                "page_number": page_number,
                "raw_item": {"html": match.group(0)},
            }
        )
    if not products:
        raise ValueError("response HTML does not contain a product list")
    return products


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TmallShopStore:
    """SQLite persistence for captured shop pages and their product items."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tmall_shop_pages (
                shop_url TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                item_count INTEGER NOT NULL,
                raw_json TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                PRIMARY KEY (shop_url, page_number)
            );
            CREATE TABLE IF NOT EXISTS tmall_shop_items (
                shop_url TEXT NOT NULL,
                item_id TEXT NOT NULL,
                title TEXT,
                price TEXT,
                original_price TEXT,
                item_url TEXT,
                image_url TEXT,
                sales TEXT,
                first_seen_page INTEGER NOT NULL,
                last_seen_page INTEGER NOT NULL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (shop_url, item_id)
            );
            """
        )
        self.conn.commit()

    def save_page(
        self,
        shop_url: str,
        page_number: int,
        raw_payload: dict[str, Any],
        items: list[dict[str, Any]],
    ) -> None:
        now = utc_now_iso()
        raw_page_json = json.dumps(raw_payload, ensure_ascii=False, separators=(",", ":"))
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO tmall_shop_pages (
                    shop_url, page_number, item_count, raw_json, captured_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(shop_url, page_number) DO UPDATE SET
                    item_count = excluded.item_count,
                    raw_json = excluded.raw_json,
                    captured_at = excluded.captured_at
                """,
                (shop_url, page_number, len(items), raw_page_json, now),
            )
            for item in items:
                self.conn.execute(
                    """
                    INSERT INTO tmall_shop_items (
                        shop_url, item_id, title, price, original_price, item_url,
                        image_url, sales, first_seen_page, last_seen_page, raw_json,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(shop_url, item_id) DO UPDATE SET
                        title = excluded.title,
                        price = excluded.price,
                        original_price = excluded.original_price,
                        item_url = excluded.item_url,
                        image_url = excluded.image_url,
                        sales = excluded.sales,
                        last_seen_page = excluded.last_seen_page,
                        raw_json = excluded.raw_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        shop_url,
                        item["item_id"],
                        item.get("title", ""),
                        item.get("price", ""),
                        item.get("original_price", ""),
                        item.get("item_url", ""),
                        item.get("image_url", ""),
                        item.get("sales", ""),
                        item["page_number"],
                        item["page_number"],
                        json.dumps(item.get("raw_item", item), ensure_ascii=False, separators=(",", ":")),
                        now,
                        now,
                    ),
                )

    def count_pages(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM tmall_shop_pages").fetchone()[0])

    def count_items(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM tmall_shop_items").fetchone()[0])

    def get_item(self, shop_url: str, item_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM tmall_shop_items WHERE shop_url = ? AND item_id = ?",
            (shop_url, item_id),
        ).fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        self.conn.close()


class CrawlValidationError(ValueError):
    """Raised when a requested page cannot be accepted as a valid result."""


@dataclass(frozen=True)
class CrawlResult:
    page_item_counts: dict[int, int]
    total_items: int
    skipped_duplicates: int = 0
    stop_reason: str = "page_limit"


def has_next_page(payload: dict[str, Any] | str) -> bool:
    """Return whether legacy Tmall async HTML enables a next-page link."""
    if not isinstance(payload, str):
        return True
    compact = " ".join(payload.split())
    page_count = re.search(
        r'<b\b[^>]*\bclass\s*=\s*(["\'])[^"\']*\bui-page-s-len\b[^"\']*\1[^>]*>\s*(\d+)\s*/\s*(\d+)\s*</b>',
        compact,
        re.IGNORECASE,
    )
    if page_count:
        return int(page_count.group(2)) < int(page_count.group(3))
    pagination = re.search(
        r'<div\b[^>]*\bclass\s*=\s*(["\'])[^"\']*\bpagination\b[^"\']*\1[^>]*>(?P<body>.*?)</div>',
        compact,
        re.IGNORECASE,
    )
    if not pagination:
        return True
    next_link = re.search(
        r'<a\b(?P<tag>[^>]*)>\s*下一页\s*</a>',
        pagination.group("body"),
        re.IGNORECASE | re.DOTALL,
    )
    if not next_link:
        return True
    return "disable" not in _html_attribute(next_link.group("tag"), "class").split()


def crawl_pages(
    shop_url: str,
    start_page: int,
    pages: int,
    fetcher: Any,
    store: TmallShopStore,
) -> CrawlResult:
    """Fetch, validate, and save exactly the requested inclusive page range."""
    if start_page <= 0:
        raise CrawlValidationError("start_page must be positive")
    if pages <= 0:
        raise CrawlValidationError("pages must be positive")

    page_item_counts: dict[int, int] = {}
    seen_item_pages: dict[str, int] = {}
    for page_number in range(start_page, start_page + pages):
        payload = fetcher(page_number)
        items = extract_products(payload, page_number)
        if not items:
            raise CrawlValidationError(f"page {page_number} is empty")
        page_item_ids: set[str] = set()
        unique_items: list[dict[str, Any]] = []
        for item in items:
            item_id = item["item_id"]
            if item_id in page_item_ids:
                continue
            if item_id in seen_item_pages:
                raise CrawlValidationError(
                    f"product ID {item_id} appears on pages "
                    f"{seen_item_pages[item_id]} and {page_number}"
                )
            seen_item_pages[item_id] = page_number
            page_item_ids.add(item_id)
            unique_items.append(item)
        store.save_page(shop_url, page_number, payload, unique_items)
        page_item_counts[page_number] = len(unique_items)
    return CrawlResult(page_item_counts=page_item_counts, total_items=len(seen_item_pages))


def crawl_until_end(
    shop_url: str,
    start_page: int,
    fetcher: Any,
    store: TmallShopStore,
) -> CrawlResult:
    """Save unique products until Tmall disables pagination or returns no items."""
    if start_page <= 0:
        raise CrawlValidationError("start_page must be positive")

    page_item_counts: dict[int, int] = {}
    seen_item_ids: set[str] = set()
    skipped_duplicates = 0
    page_number = start_page
    while True:
        payload = fetcher(page_number)
        try:
            items = extract_products(payload, page_number)
        except ValueError as exc:
            if "does not contain a product list" in str(exc):
                return CrawlResult(
                    page_item_counts,
                    len(seen_item_ids),
                    skipped_duplicates,
                    "empty_page",
                )
            raise
        if not items:
            return CrawlResult(
                page_item_counts, len(seen_item_ids), skipped_duplicates, "empty_page"
            )

        page_item_ids: set[str] = set()
        unique_items: list[dict[str, Any]] = []
        for item in items:
            item_id = item["item_id"]
            if item_id in page_item_ids:
                continue
            page_item_ids.add(item_id)
            if item_id in seen_item_ids:
                skipped_duplicates += 1
                continue
            seen_item_ids.add(item_id)
            unique_items.append(item)
        if unique_items:
            store.save_page(shop_url, page_number, payload, unique_items)
            page_item_counts[page_number] = len(unique_items)
        if not has_next_page(payload):
            return CrawlResult(
                page_item_counts,
                len(seen_item_ids),
                skipped_duplicates,
                "no_next_page",
            )
        page_number += 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl Tmall shop product-list pages into SQLite."
    )
    parser.add_argument("--shop-url", required=True, help="Tmall shop search URL.")
    parser.add_argument("--start-page", required=True, type=int, help="First page number.")
    parser.add_argument(
        "--pages",
        type=int,
        help="Optional number of pages to crawl; omit to continue until no next page.",
    )
    parser.add_argument("--db", default="data/taobao_shop_items.sqlite3", help="SQLite output path.")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds.")
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> CrawlerConfig:
    cookie_header = os.environ.get("TAOBAO_COOKIE", "").strip()
    if not cookie_header:
        raise ValueError("TAOBAO_COOKIE environment variable is required")
    cookies = parse_cookie_header(cookie_header)
    if not cookies:
        raise ValueError("TAOBAO_COOKIE does not contain any valid cookies")
    if args.start_page <= 0 or (args.pages is not None and args.pages <= 0):
        raise ValueError("--start-page and --pages must be positive")
    return CrawlerConfig(
        shop_url=args.shop_url,
        start_page=args.start_page,
        pages=args.pages,
        db_path=Path(args.db),
        timeout=args.timeout,
        cookies=cookies,
    )


def build_session():
    import requests

    session = requests.Session()
    # Avoid local system proxies that replace TLS certificates on this machine.
    session.trust_env = False
    return session


def fetch_page(config: CrawlerConfig, page_number: int, session: Any) -> dict[str, Any]:
    """Request and decode one asynchronous Tmall shop search page."""
    session.trust_env = False
    request_url, params, headers = build_page_request(config.shop_url, page_number)
    response = session.get(
        request_url,
        params=params,
        headers=headers,
        cookies=config.cookies,
        timeout=config.timeout,
    )
    response.raise_for_status()
    return decode_payload(response.text)


def configure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    configure_stdout_utf8()
    try:
        config = config_from_args(parse_args(argv))
        session = build_session()
        store = TmallShopStore(config.db_path)
        try:
            fetcher = lambda page_number: fetch_page(config, page_number, session)
            if config.pages is None:
                result = crawl_until_end(
                    config.shop_url, config.start_page, fetcher, store
                )
            else:
                result = crawl_pages(
                    config.shop_url,
                    config.start_page,
                    config.pages,
                    fetcher,
                    store,
                )
        finally:
            store.close()
    except (CrawlValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for page_number, item_count in result.page_item_counts.items():
        print(f"page={page_number} items={item_count}")
    print(
        "Crawl finished: "
        f"pages={len(result.page_item_counts)} items={result.total_items} "
        f"skipped_duplicates={result.skipped_duplicates} stop_reason={result.stop_reason}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
