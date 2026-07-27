"""
Download Taobao item images crawled today.

Organizes images as:
    images/{shop_name}/{item_title}_{num_iid}/image_01.jpg
    images/{shop_name}/{item_title}_{num_iid}/image_02.jpg
    ...

Usage:
    python src/download_images.py                     # today's items, 8 workers
    python src/download_images.py --workers 16        # more concurrency
    python src/download_images.py --all               # all items in DB
    python src/download_images.py --date 2026-07-20   # specific date
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_name(name: str, max_len: int = 60) -> str:
    """Remove characters that are invalid in Windows folder names."""
    name = (name or "unknown").strip()
    # Replace invalid chars with underscore
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Collapse multiple spaces/underscores
    name = re.sub(r'[\s_]+', '_', name)
    # Trim
    name = name.strip('_. ')
    return name[:max_len]


def ensure_url(url: str) -> str:
    """Ensure protocol-relative URLs get https: prefix."""
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return "https://" + url
    return url


# ---------------------------------------------------------------------------
# Download logic
# ---------------------------------------------------------------------------

def download_image(url: str, save_path: Path, timeout: float = 30.0) -> bool:
    """Download a single image to save_path. Returns True on success."""
    if save_path.exists():
        return True  # already downloaded

    save_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(3):
        try:
            req = Request(
                ensure_url(url),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://item.taobao.com/",
                },
            )
            with urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                if len(data) < 100:
                    raise ValueError(f"Response too small: {len(data)} bytes")
                save_path.write_bytes(data)
                return True
        except Exception:
            if attempt < 2:
                time.sleep(1)
    return False


def process_item(
    num_iid: str,
    shop_name: str,
    title: str,
    raw_json: str,
    base_dir: Path,
    timeout: float = 30.0,
) -> tuple[int, int]:
    """Download all images for one item. Returns (downloaded, failed)."""
    shop_dir = sanitize_name(shop_name)
    item_dir = sanitize_name(f"{title}_{num_iid}")
    item_path = base_dir / shop_dir / item_dir

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return 0, 0

    item_imgs = data.get("item", {}).get("item_imgs", [])
    if not isinstance(item_imgs, list) or not item_imgs:
        return 0, 0

    ok = 0
    fail = 0
    for idx, img in enumerate(item_imgs, start=1):
        url = ""
        if isinstance(img, dict):
            url = img.get("url", "")
        elif isinstance(img, str):
            url = img

        if not url:
            continue

        ext = ".jpg"
        url_lower = url.lower()
        if ".png" in url_lower:
            ext = ".png"
        elif ".webp" in url_lower:
            ext = ".webp"

        filename = f"image_{idx:02d}{ext}"
        if download_image(url, item_path / filename, timeout):
            ok += 1
        else:
            fail += 1

    return ok, fail


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Download Taobao item images")
    parser.add_argument("--db", default="data/taobao_batch.sqlite3",
                        help="SQLite database path")
    parser.add_argument("--output", default="images",
                        help="Output directory (default: images/)")
    parser.add_argument("--workers", type=int, default=8,
                        help="Concurrent download workers (default: 8)")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="Download timeout per image (default: 30s)")
    parser.add_argument("--date", default=None,
                        help="Filter by date YYYY-MM-DD (default: today)")
    parser.add_argument("--all", action="store_true",
                        help="Download images for ALL items in DB")
    args = parser.parse_args()

    # Resolve paths
    db_path = str(PROJECT_ROOT / args.db) if not os.path.isabs(args.db) else args.db
    output_dir = Path(PROJECT_ROOT / args.output) if not os.path.isabs(args.output) else Path(args.output)

    # Query items
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    if args.all:
        rows = db.execute("""
            SELECT num_iid, nick, title, raw_json
            FROM item_details
            ORDER BY updated_at DESC
        """).fetchall()
        print(f"Loading ALL {len(rows)} items from database...")
    elif args.date:
        rows = db.execute("""
            SELECT num_iid, nick, title, raw_json
            FROM item_details
            WHERE date(updated_at) = ?
            ORDER BY updated_at DESC
        """, (args.date,)).fetchall()
        print(f"Loading {len(rows)} items from {args.date}...")
    else:
        today = time.strftime("%Y-%m-%d")
        rows = db.execute("""
            SELECT num_iid, nick, title, raw_json
            FROM item_details
            WHERE date(updated_at) = ?
            ORDER BY updated_at DESC
        """, (today,)).fetchall()
        print(f"Loading {len(rows)} items from today ({today})...")
    db.close()

    if not rows:
        print("No items found.")
        return 0

    # Pre-calculate total images
    total_imgs = 0
    items_with_imgs = 0
    for r in rows:
        try:
            data = json.loads(r["raw_json"])
            imgs = data.get("item", {}).get("item_imgs", [])
            if isinstance(imgs, list) and imgs:
                total_imgs += len(imgs)
                items_with_imgs += 1
        except json.JSONDecodeError:
            pass

    print(f"Items with images: {items_with_imgs}/{len(rows)}")
    print(f"Total images: {total_imgs}")
    print(f"Output: {output_dir.resolve()}")
    print(f"Workers: {args.workers}")
    print("-" * 60)

    start_time = time.monotonic()
    total_ok = 0
    total_fail = 0
    completed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for r in rows:
            f = executor.submit(
                process_item,
                r["num_iid"],
                r["nick"] or "unknown_shop",
                r["title"] or "unknown",
                r["raw_json"],
                output_dir,
                args.timeout,
            )
            futures[f] = r["num_iid"]

        for f in as_completed(futures):
            completed += 1
            ok, fail = f.result()
            total_ok += ok
            total_fail += fail
            if completed % 50 == 0 or completed == len(rows):
                elapsed = time.monotonic() - start_time
                rate = total_ok / elapsed if elapsed > 0 else 0
                print(f"  [{completed}/{len(rows)}] "
                      f"imgs_ok={total_ok} imgs_fail={total_fail} "
                      f"| {rate:.1f} imgs/s")

    elapsed = time.monotonic() - start_time
    print(f"\n{'=' * 60}")
    print(f"Done in {elapsed:.1f}s")
    print(f"Images downloaded: {total_ok}")
    print(f"Images failed:    {total_fail}")
    print(f"Output directory:  {output_dir.resolve()}")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
