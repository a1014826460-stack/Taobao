from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

KEYWORDS = [
    "润滑液", "高潮液", "快感液", "延时喷剂", "飞机杯", "电动飞机杯", "男用自慰器", "跳蛋", "穿戴跳蛋",
    "遥控跳蛋", "情趣按摩棒", "震动棒", "AV棒", "吸吮跳蛋", "仿真阳具", "肛塞", "前列腺按摩器", "倒模", "名器",
]
TASKS = [("_sale", 20), ("", 10)]
DB = "data/jd_search.sqlite3"
LOG = Path("target") / f"jd_search_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

with LOG.open("w", encoding="utf-8") as log:
    for keyword in KEYWORDS:
        for sort, pages in TASKS:
            cmd = [
                sys.executable, "-m", "src.jd.direct.search",
                "--q", keyword,
                "--sort", sort,
                "--max-pages", str(pages),
                "--workers", "6",
                "--delay", "0.05",
                "--timeout", "45",
                "--retries", "3",
                "--db", DB,
            ]
            print(f"RUN keyword={keyword} sort={sort!r} pages={pages}", flush=True)
            log.write(f"\n=== RUN keyword={keyword} sort={sort!r} pages={pages} ===\n")
            proc = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
            log.write(proc.stdout)
            log.write(proc.stderr)
            log.write(f"\nexit={proc.returncode}\n")
            log.flush()
            print(f"DONE keyword={keyword} sort={sort!r} exit={proc.returncode}", flush=True)
print(LOG)
