from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from src.taobao.direct.search import SearchCrawlerConfig, crawl_search

KEYWORDS = [
    "润滑液", "高潮液", "快感液", "延时喷剂", "飞机杯", "电动飞机杯",
    "男用自慰器", "跳蛋", "穿戴跳蛋", "遥控跳蛋", "情趣按摩棒", "震动棒",
    "AV棒", "吸吮跳蛋", "仿真阳具", "肛塞", "前列腺按摩器", "倒模", "名器",
]
SORTS = ["_sale", "", "credit"]
DB_PATH = "data/taobao_search.sqlite3"

for raw_line in Path(".env").read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
KEY = os.environ.get("FANB_API_KEY") or os.environ.get("KEY") or ""
SECRET = os.environ.get("FANB_API_SECRET") or os.environ.get("SECRET") or ""
if not KEY or not SECRET:
    raise SystemExit("Missing FANB gateway credentials")


def unresolved_count() -> int:
    db = sqlite3.connect(DB_PATH)
    try:
        states = {}
        for fingerprint, page, status in db.execute("SELECT query_fingerprint, page, status FROM search_state"):
            data = json.loads(fingerprint)
            states[(data["q"], data["sort"], page)] = status
        return sum(
            states.get((keyword, sort, page)) != "success"
            for keyword in KEYWORDS
            for sort in SORTS
            for page in range(1, 7)
        )
    finally:
        db.close()

for round_number in range(1, 4):
    print(f"Retry round {round_number}/3; unresolved before={unresolved_count()}", flush=True)
    for keyword in KEYWORDS:
        for sort in SORTS:
            result = crawl_search(SearchCrawlerConfig(
                key=KEY, secret=SECRET, query=keyword, sort=sort, max_pages=6,
                max_workers=1, delay=3.0, retries=6, timeout=30.0, db_path=DB_PATH,
            ))
            print(
                f"{keyword} sort={sort or 'default'} fetched={result.fetched_pages} "
                f"skipped={result.skipped_pages} failed={result.failed_pages}",
                flush=True,
            )
    remaining = unresolved_count()
    print(f"Retry round {round_number}/3 complete; unresolved after={remaining}", flush=True)
    if remaining == 0:
        break
    if round_number < 3:
        time.sleep(60)
print(f"Retry job completed; unresolved={unresolved_count()}", flush=True)
