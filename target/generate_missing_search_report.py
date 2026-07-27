import csv
import json
import sqlite3
from pathlib import Path

keywords = [
    "润滑液", "高潮液", "快感液", "延时喷剂", "飞机杯", "电动飞机杯",
    "男用自慰器", "跳蛋", "穿戴跳蛋", "遥控跳蛋", "情趣按摩棒", "震动棒",
    "AV棒", "吸吮跳蛋", "仿真阳具", "肛塞", "前列腺按摩器", "倒模", "名器",
]
sorts = [("_sale", "销量"), ("", "综合"), ("credit", "credit")]
db = sqlite3.connect("data/taobao_search.sqlite3")
states = {}
for fingerprint, page, status, error, updated_at in db.execute(
    "SELECT query_fingerprint, page, status, last_error, updated_at FROM search_state"
):
    data = json.loads(fingerprint)
    states[(data["q"], data["sort"], page)] = (status, error, updated_at)
rows = []
for keyword in keywords:
    for sort, sort_name in sorts:
        for page in range(1, 7):
            status, error, updated_at = states.get((keyword, sort, page), ("missing_state", "", ""))
            if status != "success":
                rows.append({
                    "keyword": keyword,
                    "sort": sort,
                    "sort_name": sort_name,
                    "page": page,
                    "status": status,
                    "last_error": error,
                    "updated_at": updated_at,
                })
db.close()
path = Path("target/missing_taobao_search_pages_20260726.csv")
with path.open("w", newline="", encoding="utf-8") as output:
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print(f"wrote {len(rows)} rows to {path}")
