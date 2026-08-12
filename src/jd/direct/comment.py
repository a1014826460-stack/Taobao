"""Resumable JD first-page comment crawler."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMMENT_API_URL = "http://115.29.242.83:8000/jdpl/get_item"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class JDCommentCrawlerConfig:
    token: str
    itemids: list[str]
    db_path: str = "data/jd_huangxiaomi_comments.sqlite3"
    reset_items: bool = False
    delay: float = 0.2
    timeout: float = 30.0
    retries: int = 2


@dataclass(frozen=True)
class JDCommentCrawlResult:
    total: int
    fetched: int
    skipped: int
    failed: int


class SQLiteJDCommentStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS jd_item_comments (
                itemid TEXT PRIMARY KEY,
                page INTEGER NOT NULL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jd_comment_state (
                itemid TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def get_state(self, itemid: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM jd_comment_state WHERE itemid = ?", (str(itemid),)).fetchone()
        return dict(row) if row else None

    def get_comment(self, itemid: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM jd_item_comments WHERE itemid = ?", (str(itemid),)).fetchone()
        return dict(row) if row else None

    def mark_pending(self, itemid: str) -> None:
        self._upsert_state(itemid, "pending")

    def mark_error(self, itemid: str, error: Exception) -> None:
        self._upsert_state(itemid, "error", str(error))

    def save_comment(self, itemid: str, response: dict) -> None:
        now = utc_now_iso()
        with self.conn:
            self.conn.execute("""
                INSERT INTO jd_item_comments (itemid, page, raw_json, created_at, updated_at)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(itemid) DO UPDATE SET page=excluded.page, raw_json=excluded.raw_json, updated_at=excluded.updated_at
            """, (str(itemid), json.dumps(response, ensure_ascii=False), now, now))
            self._upsert_state(itemid, "success")

    def _upsert_state(self, itemid: str, status: str, last_error: str | None = None) -> None:
        now = utc_now_iso()
        with self.conn:
            self.conn.execute("""
                INSERT INTO jd_comment_state (itemid, status, last_error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(itemid) DO UPDATE SET status=excluded.status, last_error=excluded.last_error, updated_at=excluded.updated_at
            """, (str(itemid), status, last_error, now, now))


def fetch_jd_comment(config: JDCommentCrawlerConfig, itemid: str, opener=urlopen) -> dict:
    request = Request(
        f"{COMMENT_API_URL}?{urlencode({'token': config.token, 'itemid': str(itemid), 'page': 1})}",
        headers={"User-Agent": "jd-comment-crawler/1.0"},
    )
    last_error = None
    for attempt in range(1, int(config.retries) + 1):
        try:
            with opener(request, timeout=float(config.timeout)) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("comment API response is not a JSON object")
            return payload
        except Exception as exc:
            last_error = exc
            if attempt < int(config.retries):
                time.sleep(min(attempt, 3))
    raise RuntimeError(f"request failed after {config.retries} attempt(s): {last_error}")


def crawl_jd_comments(config: JDCommentCrawlerConfig, fetcher=None, store=None) -> JDCommentCrawlResult:
    if not config.token:
        raise ValueError("JD_COMMENT_TOKEN must not be empty")
    if config.retries <= 0:
        raise ValueError("retries must be a positive integer")
    active_fetcher = fetcher or fetch_jd_comment
    owns_store = store is None
    store = store or SQLiteJDCommentStore(config.db_path)
    fetched = skipped = failed = 0
    try:
        for itemid in dict.fromkeys(str(value) for value in config.itemids if str(value).strip()):
            state = store.get_state(itemid)
            if state and state["status"] == "success" and not config.reset_items:
                skipped += 1
                continue
            store.mark_pending(itemid)
            try:
                response = active_fetcher(config, itemid)
                if not isinstance(response, dict):
                    raise ValueError("comment API response is not a JSON object")
                store.save_comment(itemid, response)
                fetched += 1
            except Exception as exc:
                store.mark_error(itemid, exc)
                failed += 1
            if config.delay:
                time.sleep(float(config.delay))
        return JDCommentCrawlResult(len(dict.fromkeys(config.itemids)), fetched, skipped, failed)
    finally:
        if owns_store:
            store.close()


def load_successful_item_ids(detail_db_path: str | Path) -> list[str]:
    conn = sqlite3.connect(str(detail_db_path))
    try:
        return [str(row[0]) for row in conn.execute("SELECT num_iid FROM jd_item_state WHERE status = 'success' ORDER BY num_iid")]
    finally:
        conn.close()


def _load_dotenv() -> None:
    path = PROJECT_ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resumable JD first-page comment crawler")
    parser.add_argument("--detail-db", default="data/jd_huangxiaomi_item_details.sqlite3")
    parser.add_argument("--db", default="data/jd_huangxiaomi_comments.sqlite3")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--reset-items", action="store_true")
    return parser


def main(argv=None) -> int:
    try:
        args = build_arg_parser().parse_args(argv)
        _load_dotenv()
        token = os.environ.get("JD_COMMENT_TOKEN", "")
        itemids = load_successful_item_ids(args.detail_db)
        if args.limit > 0:
            itemids = itemids[:args.limit]
        result = crawl_jd_comments(JDCommentCrawlerConfig(
            token=token, itemids=itemids, db_path=args.db, reset_items=args.reset_items,
            delay=args.delay, timeout=args.timeout, retries=args.retries,
        ))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"JD comment crawl finished: total={result.total} fetched={result.fetched} skipped={result.skipped} failed={result.failed}")
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
