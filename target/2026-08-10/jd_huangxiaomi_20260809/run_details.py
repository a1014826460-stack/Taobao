import csv
import os
import threading
import time
from dataclasses import replace
from pathlib import Path
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from src.jd.direct.item import (
    JDItemCrawlerConfig,
    SQLiteJDItemStore,
    fetch_jd_item_detail,
    parse_jd_item_response,
)


OUT = Path("target/jd_huangxiaomi_20260809")
LOG = OUT / "detail_run.log"


def log(text):
    print(text, flush=True)
    with LOG.open("a", encoding="utf-8") as file:
        file.write(text + "\n")


def load_env():
    for raw in Path(".env").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env()
key = os.environ.get("FANB_API_KEY") or os.environ.get("KEY")
secret = os.environ.get("FANB_API_SECRET") or os.environ.get("SECRET")
with (OUT / "detail_candidates.csv").open(encoding="utf-8-sig", newline="") as file:
    rows = list(csv.DictReader(file))

store = SQLiteJDItemStore("data/jd_huangxiaomi_item_details.sqlite3")
marker = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
(OUT / "detail_run_started_at.txt").write_text(marker + "\n", encoding="utf-8")
with store.conn:
    store.conn.executemany(
        "INSERT OR IGNORE INTO jd_item_sources(keyword,sort,page,num_iid,created_at) VALUES(?,?,?,?,?)",
        [(row["keyword"], row["sort"], int(row["page"]), row["num_iid"], marker) for row in rows],
    )

normal = JDItemCrawlerConfig(
    key=key, secret=secret, num_iids=[], db_path="data/jd_huangxiaomi_item_details.sqlite3",
    timeout=30, retries=1, item_api="item_get", delay=0,
)
pro = replace(normal, item_api="item_get_pro")
last_request = 0.0
throttle = threading.Lock()
stop = threading.Event()


def is_billing(exc):
    return "4016" in str(exc) or "欠费" in str(exc)


def call(num_iid):
    global last_request
    prior = None
    for config in (normal, pro):
        with throttle:
            remaining = last_request + 0.15 - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
            last_request = time.monotonic()
        try:
            response = fetch_jd_item_detail(config, num_iid)
            parse_jd_item_response(response)
            return "success_pro" if config.item_api == "item_get_pro" else "success", response
        except Exception as exc:
            if is_billing(exc):
                return "billing", exc
            prior = exc
    return "error", prior


pending = []
skipped = 0
for row in rows:
    state = store.get_item_state(row["num_iid"])
    if state and state["status"] == "success":
        skipped += 1
    else:
        store.mark_pending(row["num_iid"])
        pending.append(row["num_iid"])

log(f"start candidates={len(rows)} pending={len(pending)} skipped={skipped}")
done = fetched = failed = pro_success = index = 0
futures = {}
try:
    with ThreadPoolExecutor(max_workers=4) as executor:
        while (index < len(pending) or futures) and not stop.is_set():
            while index < len(pending) and len(futures) < 4 and not stop.is_set():
                num_iid = pending[index]
                index += 1
                futures[executor.submit(call, num_iid)] = num_iid
            complete, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in complete:
                num_iid = futures.pop(future)
                status, payload = future.result()
                done += 1
                if status.startswith("success"):
                    store.save_item_detail(num_iid, payload)
                    fetched += 1
                    pro_success += status == "success_pro"
                else:
                    store.mark_error(num_iid, payload)
                    failed += 1
                    if status == "billing":
                        stop.set()
                        log(f"STOP billing iid={num_iid} error={payload}")
                if done % 25 == 0 or status == "billing":
                    log(f"progress done={done} submitted={index}/{len(pending)} fetched={fetched} pro_success={pro_success} failed={failed} skipped={skipped}")
finally:
    store.close()

log(f"finished done={done} submitted={index} fetched={fetched} pro_success={pro_success} failed={failed} skipped={skipped} stopped={stop.is_set()}")
if stop.is_set():
    raise SystemExit(2)
