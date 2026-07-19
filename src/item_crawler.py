import json
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


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


@dataclass
class ItemCrawlerConfig:
    key: str
    secret: str
    num_iids: list[str]
    db_path: str = "data/taobao_shop_items.sqlite3"
    reset_items: bool = False
    lang: str = "zh-CN"
    delay: float = 0.5
    timeout: float = 20.0
    retries: int = 3
    item_api: str = "item_get_pro"
    is_promotion: str | None = None


@dataclass(frozen=True)
class ItemCrawlResult:
    total: int
    fetched: int
    skipped: int
    failed: int


class SQLiteItemStore:
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

    def mark_pending(self, num_iid):
        self._upsert_state(num_iid, "pending")

    def mark_skipped(self, num_iid):
        self._upsert_state(num_iid, "skipped")

    def mark_error(self, num_iid, error):
        self._upsert_state(num_iid, "error", str(error))

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
    if fetcher is None:
        fetcher = fetch_item_detail
    owns_store = store is None
    if store is None:
        store = SQLiteItemStore(config.db_path)

    fetched = 0
    skipped = 0
    failed = 0
    try:
        for num_iid in config.num_iids:
            state = store.get_item_state(num_iid)
            if (
                state
                and state.get("status") == "success"
                and not config.reset_items
            ):
                skipped += 1
                continue

            store.mark_pending(num_iid)
            try:
                response = fetcher(config, num_iid)
                parse_item_response(response)
                store.save_item_detail(num_iid, response)
                fetched += 1
            except Exception as exc:
                store.mark_error(num_iid, exc)
                failed += 1
            if config.delay:
                time.sleep(float(config.delay))
        return ItemCrawlResult(
            total=len(config.num_iids),
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
