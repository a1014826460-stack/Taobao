"""Quick progress checker for the batch crawler. Run anytime to see live stats.

Usage:
    python src/check_progress.py
    python src/check_progress.py --watch    # auto-refresh every 30s
"""
import sqlite3
import sys
import time
from pathlib import Path

# Fix GBK encoding issues on Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "taobao_batch.sqlite3"
TOTAL = 5000


def check():
    if not DB_PATH.exists():
        print("DB not created yet - crawler hasn't started.")
        return

    db = sqlite3.connect(str(DB_PATH))
    total = db.execute("SELECT COUNT(*) FROM item_detail_state").fetchone()[0]
    success = db.execute(
        "SELECT COUNT(*) FROM item_detail_state WHERE status='success'"
    ).fetchone()[0]
    failed = db.execute(
        "SELECT COUNT(*) FROM item_detail_state WHERE status='error'"
    ).fetchone()[0]
    complete = success + failed
    pct = 100 * complete / TOTAL

    bar_len = 30
    filled = int(bar_len * complete / TOTAL)
    bar = "#" * filled + "-" * (bar_len - filled)

    print(f"\n{'=' * 55}")
    print(f"  Taobao Batch Crawler Progress")
    print(f"{'=' * 55}")
    print(f"  [{bar}] {pct:.1f}%")
    print(f"  Complete: {complete}/{TOTAL}")
    print(f"  Success:  {success}")
    print(f"  Failed:   {failed}")
    print(f"  Time:     {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 55}")

    # Latest 5 items
    latest = db.execute(
        "SELECT num_iid, title, price, nick FROM item_details ORDER BY updated_at DESC LIMIT 5"
    ).fetchall()
    if latest:
        print(f"\n  Latest {min(5, len(latest))} items:")
        for r in latest:
            title = (r[1] or "")[:50]
            shop = (r[3] or "")[:20]
            print(f"  [{r[0]}] ${r[2]} | {shop} | {title}")

    db.close()

    if complete >= TOTAL:
        print(f"\n  All done!")


if __name__ == "__main__":
    watch = "--watch" in sys.argv
    while True:
        check()
        if not watch:
            break
        time.sleep(30)
