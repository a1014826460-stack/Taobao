import argparse
import json
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


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


@dataclass
class JDItemCrawlerConfig:
    key: str
    secret: str
    num_iids: list[str]
    db_path: str = "data/jd_item_details.sqlite3"
    reset_items: bool = False
    cache: str = "no"
    lang: str = "zh-CN"
    delay: float = 0.5
    timeout: float = 20.0
    retries: int = 3


@dataclass(frozen=True)
class JDItemCrawlResult:
    total: int
    fetched: int
    skipped: int
    failed: int


class SQLiteJDItemStore:
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
            CREATE TABLE IF NOT EXISTS jd_item_details (
                num_iid TEXT PRIMARY KEY,
                title TEXT,
                price TEXT,
                orginal_price TEXT,
                nick TEXT,
                detail_url TEXT,
                pic_url TEXT,
                brand TEXT,
                cid TEXT,
                shop_id TEXT,
                sales TEXT,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jd_item_state (
                num_iid TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def get_item_state(self, num_iid):
        row = self.conn.execute(
            "SELECT * FROM jd_item_state WHERE num_iid = ?",
            (str(num_iid),),
        ).fetchone()
        return dict(row) if row else None

    def get_item_detail(self, num_iid):
        row = self.conn.execute(
            "SELECT * FROM jd_item_details WHERE num_iid = ?",
            (str(num_iid),),
        ).fetchone()
        return dict(row) if row else None

    def count_successful(self):
        row = self.conn.execute(
            "SELECT COUNT(*) AS total FROM jd_item_state WHERE status = 'success'"
        ).fetchone()
        return int(row["total"])

    def mark_pending(self, num_iid):
        self._upsert_state(num_iid, "pending")

    def mark_error(self, num_iid, error):
        self._upsert_state(num_iid, "error", str(error))

    def save_item_detail(self, num_iid, response):
        now = utc_now_iso()
        item = response.get("item") or {}
        actual_num_iid = str(item.get("num_iid") or num_iid)
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO jd_item_details (
                    num_iid, title, price, orginal_price, nick, detail_url,
                    pic_url, brand, cid, shop_id, sales, raw_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(num_iid) DO UPDATE SET
                    title = excluded.title,
                    price = excluded.price,
                    orginal_price = excluded.orginal_price,
                    nick = excluded.nick,
                    detail_url = excluded.detail_url,
                    pic_url = excluded.pic_url,
                    brand = excluded.brand,
                    cid = excluded.cid,
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
                INSERT INTO jd_item_state (
                    num_iid, status, last_error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(num_iid) DO UPDATE SET
                    status = excluded.status,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (str(num_iid), status, last_error, now, now),
            )


def parse_jd_item_response(response):
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


def crawl_jd_items(config, fetcher=None, store=None):
    if fetcher is None:
        fetcher = fetch_jd_item_detail
    owns_store = store is None
    if store is None:
        store = SQLiteJDItemStore(config.db_path)

    fetched = 0
    skipped = 0
    failed = 0
    try:
        for num_iid in config.num_iids:
            state = store.get_item_state(num_iid)
            if state and state.get("status") == "success" and not config.reset_items:
                skipped += 1
                continue

            store.mark_pending(num_iid)
            try:
                response = fetcher(config, num_iid)
                parse_jd_item_response(response)
                store.save_item_detail(num_iid, response)
                fetched += 1
            except Exception as exc:
                store.mark_error(num_iid, exc)
                failed += 1
            if config.delay:
                time.sleep(float(config.delay))
        return JDItemCrawlResult(
            total=len(config.num_iids),
            fetched=fetched,
            skipped=skipped,
            failed=failed,
        )
    finally:
        if owns_store:
            store.close()


def fetch_jd_item_detail(config, num_iid, opener=urlopen):
    base_url = "https://api-gw.fan-b.com/jd/item_get_pro/"
    params = {
        "key": config.key,
        "num_iid": str(num_iid),
        "cache": config.cache,
        "lang": config.lang,
        "secret": config.secret,
    }
    url = f"{base_url}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "jd-item-crawler/1.0"})
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
        description="Lightweight resumable crawler for Fan-B JD item_get_pro API."
    )
    parser.add_argument("--env", default="password.env", help="Path to key/secret env file.")
    parser.add_argument(
        "--db",
        default=str(Path("data") / "jd_item_details.sqlite3"),
        help="SQLite database path.",
    )
    parser.add_argument(
        "--num-iids",
        action="append",
        default=[],
        required=False,
        help="JD item IDs. Supports comma, whitespace, and repeated arguments.",
    )
    parser.add_argument(
        "--num-iids-file",
        action="append",
        default=[],
        help="Text file containing item IDs separated by comma, whitespace, or newline.",
    )
    parser.add_argument(
        "--reset-items",
        action="store_true",
        help="Refetch item details even when a num_iid already has success state.",
    )
    parser.add_argument("--cache", default="no", help="API cache parameter.")
    parser.add_argument("--lang", default="zh-CN", help="API language parameter.")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between requests.")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds.")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retries per request.")
    return parser


def parse_cli_args(parser, argv=None):
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.num_iids and not args.num_iids_file:
        parser.error("No num_iid values provided. Use --num-iids or --num-iids-file.")
    return args


def config_from_args(args):
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

    return JDItemCrawlerConfig(
        key=env["key"],
        secret=env["secret"],
        num_iids=num_iids,
        db_path=str(args.db),
        reset_items=bool(args.reset_items),
        cache=str(args.cache),
        lang=str(args.lang),
        delay=float(args.delay),
        timeout=float(args.timeout),
        retries=int(args.retries),
    )


def main(argv=None):
    parser = build_arg_parser()
    args = parse_cli_args(parser, argv)
    try:
        config = config_from_args(args)
        result = crawl_jd_items(config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "JD item crawl finished: "
        f"total={result.total} fetched={result.fetched} "
        f"skipped={result.skipped} failed={result.failed}"
    )
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
