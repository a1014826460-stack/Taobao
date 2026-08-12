"""Fetch JD item details via Fan-B gateway and export as JSON."""

import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api-gw.fan-b.com/jd/item_get_pro/"
KEY = "t3727744565"
SECRET = "45652155"

ITEM_IDS = [
    "10147072608797",
    "100282300305",
    "100270678528",
    "100193444310",
    "100260782330",
]

OUTPUT = Path("target/jd_items_export.json")


def fetch_item(num_iid: str) -> dict:
    params = {
        "key": KEY,
        "num_iid": num_iid,
        "cache": "no",
        "lang": "zh-CN",
        "secret": SECRET,
    }
    url = f"{API_URL}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "jd-item-crawler/1.0"})

    for attempt in range(1, 4):
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
            return json.loads(body)
        except Exception as exc:
            if attempt == 3:
                return {"error": str(exc), "num_iid": num_iid}
            time.sleep(min(attempt, 5))
    return {}


def main():
    results = []
    for i, num_iid in enumerate(ITEM_IDS, 1):
        print(f"[{i}/{len(ITEM_IDS)}] Fetching {num_iid} ...")
        data = fetch_item(num_iid)
        error_code = data.get("error_code", "")
        if error_code and error_code != "0000":
            print(f"  [API_ERROR] {data.get('reason', data.get('error', ''))}")
        elif "error" in data:
            print(f"  [FAIL] {data['error']}")
        else:
            item = data.get("item", {})
            title = item.get("title", "N/A")
            price = item.get("price", "N/A")
            print(f"  [OK] {title}  |  price={price}")
        results.append(data)
        if i < len(ITEM_IDS):
            time.sleep(0.5)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone — exported {len(results)} records to {OUTPUT}")


if __name__ == "__main__":
    main()
