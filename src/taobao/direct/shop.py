import argparse
import json
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.taobao.direct.item import ItemCrawlerConfig, crawl_items, parse_num_iids


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_env(path):
    values = {}
    env_path = Path(path)
    with env_path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass(frozen=True)
class PageSaveResult:
    inserted_items: int
    total_items: int


@dataclass
class CrawlerConfig:
    key: str
    secret: str
    seller_id: str = "2200684271326"
    shop_id: str = "517932711"
    max_items: int = 100
    db_path: str = "data/taobao_shop_items.sqlite3"
    start_page: int = 1
    reset: bool = False
    sort: str = ""
    cache: str = "no"
    lang: str = "zh-CN"
    delay: float = 0.5
    timeout: float = 20.0
    retries: int = 3


@dataclass(frozen=True)
class CrawlResult:
    shop_id: str
    status: str
    saved_items: int
    pages_fetched: int
    next_page: int
    last_error: str | None = None


class SQLiteStore:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self):
        self.conn.close()

    def _init_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS crawl_state (
                shop_id TEXT PRIMARY KEY,
                seller_id TEXT NOT NULL,
                next_page INTEGER NOT NULL,
                fetched_items INTEGER NOT NULL DEFAULT 0,
                page_count INTEGER,
                total_results INTEGER,
                status TEXT NOT NULL,
                last_error TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS shop_pages (
                shop_id TEXT NOT NULL,
                page INTEGER NOT NULL,
                seller_id TEXT NOT NULL,
                item_count INTEGER NOT NULL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (shop_id, page)
            );

            CREATE TABLE IF NOT EXISTS shop_items (
                num_iid TEXT PRIMARY KEY,
                shop_id TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                title TEXT,
                pic_url TEXT,
                promotion_price TEXT,
                price TEXT,
                shop_name TEXT,
                detail_url TEXT,
                first_seen_page INTEGER NOT NULL,
                last_seen_page INTEGER NOT NULL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def get_state(self, shop_id):
        row = self.conn.execute(
            "SELECT * FROM crawl_state WHERE shop_id = ?",
            (str(shop_id),),
        ).fetchone()
        return dict(row) if row else None

    def count_items(self, shop_id):
        row = self.conn.execute(
            "SELECT COUNT(*) AS total FROM shop_items WHERE shop_id = ?",
            (str(shop_id),),
        ).fetchone()
        return int(row["total"])

    def save_page(self, shop_id, seller_id, page, response, next_page, status, last_error=None):
        now = utc_now_iso()
        items_node = response.get("items") or {}
        items = items_node.get("item") or []
        page_count = _to_int(items_node.get("page_count"))
        total_results = _to_int(items_node.get("total_results"))
        inserted = 0

        with self.conn:
            self.conn.execute(
                """
                INSERT INTO shop_pages (
                    shop_id, page, seller_id, item_count, raw_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(shop_id, page) DO UPDATE SET
                    seller_id = excluded.seller_id,
                    item_count = excluded.item_count,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                (
                    str(shop_id),
                    int(page),
                    str(seller_id),
                    len(items),
                    json.dumps(response, ensure_ascii=False),
                    now,
                    now,
                ),
            )

            for item in items:
                num_iid = str(item.get("num_iid", "")).strip()
                if not num_iid:
                    continue
                exists = self.conn.execute(
                    "SELECT 1 FROM shop_items WHERE num_iid = ?",
                    (num_iid,),
                ).fetchone()
                if exists is None:
                    inserted += 1
                self.conn.execute(
                    """
                    INSERT INTO shop_items (
                        num_iid, shop_id, seller_id, title, pic_url, promotion_price,
                        price, shop_name, detail_url, first_seen_page, last_seen_page,
                        raw_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(num_iid) DO UPDATE SET
                        shop_id = excluded.shop_id,
                        seller_id = excluded.seller_id,
                        title = excluded.title,
                        pic_url = excluded.pic_url,
                        promotion_price = excluded.promotion_price,
                        price = excluded.price,
                        shop_name = excluded.shop_name,
                        detail_url = excluded.detail_url,
                        last_seen_page = excluded.last_seen_page,
                        raw_json = excluded.raw_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        num_iid,
                        str(shop_id),
                        str(seller_id),
                        item.get("title"),
                        item.get("pic_url"),
                        item.get("promotion_price"),
                        item.get("price"),
                        item.get("shop_name"),
                        item.get("detail_url"),
                        int(page),
                        int(page),
                        json.dumps(item, ensure_ascii=False),
                        now,
                        now,
                    ),
                )

            total_for_shop = self.count_items(shop_id)
            self.conn.execute(
                """
                INSERT INTO crawl_state (
                    shop_id, seller_id, next_page, fetched_items, page_count,
                    total_results, status, last_error, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(shop_id) DO UPDATE SET
                    seller_id = excluded.seller_id,
                    next_page = excluded.next_page,
                    fetched_items = excluded.fetched_items,
                    page_count = excluded.page_count,
                    total_results = excluded.total_results,
                    status = excluded.status,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (
                    str(shop_id),
                    str(seller_id),
                    int(next_page),
                    total_for_shop,
                    page_count,
                    total_results,
                    status,
                    last_error,
                    now,
                ),
            )

        return PageSaveResult(inserted_items=inserted, total_items=self.count_items(shop_id))

    def update_state(
        self,
        shop_id,
        seller_id,
        next_page,
        status,
        fetched_items=None,
        page_count=None,
        total_results=None,
        last_error=None,
    ):
        now = utc_now_iso()
        if fetched_items is None:
            fetched_items = self.count_items(shop_id)
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO crawl_state (
                    shop_id, seller_id, next_page, fetched_items, page_count,
                    total_results, status, last_error, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(shop_id) DO UPDATE SET
                    seller_id = excluded.seller_id,
                    next_page = excluded.next_page,
                    fetched_items = excluded.fetched_items,
                    page_count = COALESCE(excluded.page_count, crawl_state.page_count),
                    total_results = COALESCE(excluded.total_results, crawl_state.total_results),
                    status = excluded.status,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (
                    str(shop_id),
                    str(seller_id),
                    int(next_page),
                    int(fetched_items),
                    page_count,
                    total_results,
                    status,
                    last_error,
                    now,
                ),
            )


def _to_int(value, default=None):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_items_response(response):
    if not isinstance(response, dict):
        raise ValueError("API response is not a JSON object")
    error_code = str(response.get("error_code", ""))
    if error_code and error_code != "0000":
        reason = response.get("reason") or response.get("error") or "API error"
        raise ValueError(f"API returned error_code={error_code}: {reason}")
    items_node = response.get("items")
    if not isinstance(items_node, dict):
        raise ValueError("API response missing items object")
    items = items_node.get("item") or []
    if not isinstance(items, list):
        raise ValueError("API response items.item is not a list")
    return {
        "items": items,
        "page": _to_int(items_node.get("page"), 1),
        "page_count": _to_int(items_node.get("page_count"), 1),
        "total_results": _to_int(items_node.get("total_results")),
    }


def crawl_shop(config, fetcher=None, store=None):
    if fetcher is None:
        fetcher = fetch_page
    owns_store = store is None
    if store is None:
        store = SQLiteStore(config.db_path)

    try:
        state = None if config.reset else store.get_state(config.shop_id)
        page = int(state["next_page"]) if state else int(config.start_page)
        pages_fetched = 0
        status = "running"
        last_error = None
        previous_page_ids = None

        while store.count_items(config.shop_id) < int(config.max_items):
            try:
                response = fetcher(config, page)
                parsed = parse_items_response(response)
            except Exception as exc:
                last_error = str(exc)
                store.update_state(
                    config.shop_id,
                    config.seller_id,
                    page,
                    "error",
                    last_error=last_error,
                )
                return CrawlResult(
                    shop_id=str(config.shop_id),
                    status="error",
                    saved_items=store.count_items(config.shop_id),
                    pages_fetched=pages_fetched,
                    next_page=page,
                    last_error=last_error,
                )

            pages_fetched += 1
            next_page = page + 1
            page_count = parsed["page_count"] or page
            items = parsed["items"]
            current_page_ids = [str(item.get("num_iid", "")).strip() for item in items]
            if not items:
                status = "empty_page"
            elif previous_page_ids is not None and current_page_ids == previous_page_ids:
                status = "duplicate_page"
            elif page >= page_count:
                status = "finished"
            else:
                status = "running"

            save_result = store.save_page(
                shop_id=config.shop_id,
                seller_id=config.seller_id,
                page=page,
                response=response,
                next_page=next_page,
                status=status,
            )

            if save_result.total_items >= int(config.max_items):
                status = "max_items_reached"
                store.update_state(
                    config.shop_id,
                    config.seller_id,
                    next_page,
                    status,
                    fetched_items=save_result.total_items,
                    page_count=page_count,
                    total_results=parsed["total_results"],
                )
                break
            if status in {"finished", "empty_page", "duplicate_page"}:
                break
            previous_page_ids = current_page_ids
            page = next_page
            if config.delay:
                time.sleep(float(config.delay))

        saved_items = store.count_items(config.shop_id)
        if saved_items >= int(config.max_items):
            status = "max_items_reached"
        elif status == "running":
            status = "finished"
        final_state = store.get_state(config.shop_id)
        final_next_page = int(final_state["next_page"]) if final_state else page
        return CrawlResult(
            shop_id=str(config.shop_id),
            status=status,
            saved_items=saved_items,
            pages_fetched=pages_fetched,
            next_page=final_next_page,
            last_error=last_error,
        )
    finally:
        if owns_store:
            store.close()


def fetch_page(config, page, opener=urlopen):
    base_url = "https://api-gw.fan-b.com/taobao/item_search_shop_pro/"
    params = {
        "key": config.key,
        "seller_id": config.seller_id,
        "shop_id": config.shop_id,
        "page": int(page),
        "sort": config.sort,
        "cache": config.cache,
        "lang": config.lang,
        "secret": config.secret,
    }
    url = f"{base_url}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "taobao-shop-crawler/1.0"})
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


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Lightweight resumable crawler for Fan-B Taobao APIs."
    )
    subparsers = parser.add_subparsers(dest="command")

    shop_parser = subparsers.add_parser(
        "shop",
        help="Crawl shop item list with item_search_shop_pro.",
    )
    add_common_args(shop_parser)
    shop_parser.add_argument("--seller-id", default="2200684271326", help="Taobao seller_id.")
    shop_parser.add_argument("--shop-id", default="517932711", help="Taobao shop_id.")
    shop_parser.add_argument(
        "--max-items",
        type=int,
        default=100,
        help="Stop after at least this many saved items for the shop.",
    )
    shop_parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Page to start from on new crawls.",
    )
    shop_parser.add_argument("--sort", default="", help="API sort parameter.")
    shop_parser.add_argument("--cache", default="no", help="API cache parameter.")
    shop_parser.add_argument(
        "--reset",
        action="store_true",
        help="Ignore saved next_page and start from --start-page. Existing items remain deduplicated.",
    )

    item_parser = subparsers.add_parser(
        "item",
        help="Crawl item details with item_get_pro.",
    )
    add_common_args(item_parser)
    item_parser.add_argument(
        "--num-iids",
        action="append",
        default=[],
        help="Item IDs. Supports comma, whitespace, and repeated arguments.",
    )
    item_parser.add_argument(
        "--num-iids-file",
        action="append",
        default=[],
        help="Text file containing item IDs separated by comma, whitespace, or newline.",
    )
    item_parser.add_argument(
        "--reset-items",
        action="store_true",
        help="Refetch item details even when a num_iid already has success state.",
    )
    item_parser.add_argument(
        "--api",
        choices=["item_get_pro", "item_get"],
        default="item_get_pro",
        help="Item detail API endpoint to use.",
    )
    item_parser.add_argument(
        "--is-promotion",
        default=None,
        help="Optional is_promotion parameter for the item_get endpoint.",
    )
    return parser


def add_common_args(parser):
    parser.add_argument("--env", default="password.env", help="Path to key/secret env file.")
    parser.add_argument(
        "--db",
        default=str(Path("data") / "taobao_shop_items.sqlite3"),
        help="SQLite database path.",
    )
    parser.add_argument("--lang", default="zh-CN", help="API language parameter.")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between requests.")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds.")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retries per request.")


def parse_cli_args(parser, argv=None):
    args_list = list(sys.argv[1:] if argv is None else argv)
    if not args_list or args_list[0] not in {"shop", "item", "-h", "--help"}:
        args_list.insert(0, "shop")
    return parser.parse_args(args_list)


def config_from_args(args):
    env = load_env(args.env)
    missing = [name for name in ("key", "secret") if not env.get(name)]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required value(s) in {args.env}: {joined}")
    return CrawlerConfig(
        key=env["key"],
        secret=env["secret"],
        seller_id=str(args.seller_id),
        shop_id=str(args.shop_id),
        max_items=int(args.max_items),
        db_path=str(args.db),
        start_page=int(args.start_page),
        reset=bool(args.reset),
        sort=str(args.sort),
        cache=str(args.cache),
        lang=str(args.lang),
        delay=float(args.delay),
        timeout=float(args.timeout),
        retries=int(args.retries),
    )


def config_from_item_args(args):
    env = load_env(args.env)
    missing = [name for name in ("key", "secret") if not env.get(name)]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required value(s) in {args.env}: {joined}")

    raw_values = list(args.num_iids or [])
    for file_path in args.num_iids_file or []:
        raw_values.append(Path(file_path).read_text(encoding="utf-8"))
    num_iids = parse_num_iids(raw_values)
    if not num_iids:
        raise ValueError("No num_iid values provided. Use --num-iids or --num-iids-file.")

    return ItemCrawlerConfig(
        key=env["key"],
        secret=env["secret"],
        num_iids=num_iids,
        db_path=str(args.db),
        reset_items=bool(args.reset_items),
        lang=str(args.lang),
        delay=float(args.delay),
        timeout=float(args.timeout),
        retries=int(args.retries),
        item_api=str(args.api),
        is_promotion=args.is_promotion,
    )


def main(argv=None):
    parser = build_arg_parser()
    args = parse_cli_args(parser, argv)
    try:
        if args.command == "item":
            config = config_from_item_args(args)
            item_result = crawl_items(config)
            print(
                "Item crawl finished: "
                f"total={item_result.total} fetched={item_result.fetched} "
                f"skipped={item_result.skipped} failed={item_result.failed}"
            )
            return 0 if item_result.failed == 0 else 1

        config = config_from_args(args)
        result = crawl_shop(config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "Crawl finished: "
        f"shop_id={result.shop_id} status={result.status} "
        f"saved_items={result.saved_items} pages_fetched={result.pages_fetched} "
        f"next_page={result.next_page}"
    )
    if result.last_error:
        print(f"Last error: {result.last_error}", file=sys.stderr)
        return 1
    return 0 if result.status != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
