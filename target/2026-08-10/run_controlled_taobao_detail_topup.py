import csv, os, sqlite3, sys, time
from pathlib import Path
from dataclasses import replace
from src.tools import topup_taobao_item_details as topup
from src.taobao.direct.item import ItemCrawlerConfig, SQLiteItemStore

keywords=topup.DEFAULT_KEYWORDS; target=200
candidate_csv=Path('target/taobao_detail_gap_20260729/controlled_candidates.csv')
run_log=Path('target/taobao_detail_gap_20260729/controlled_run.log')
start_marker='2026-07-29T09:54:00+00:00'

def log(msg):
    print(msg, flush=True)
    with run_log.open('a', encoding='utf-8') as f:
        f.write(msg+'\n')

# dotenv
for raw in Path('.env').read_text(encoding='utf-8').splitlines():
    line=raw.strip()
    if line and not line.startswith('#') and '=' in line:
        k,_,v=line.partition('=')
        os.environ.setdefault(k.strip(), v.strip().strip('"\''))
key=os.environ.get('FANB_API_KEY') or os.environ.get('KEY') or ''
secret=os.environ.get('FANB_API_SECRET') or os.environ.get('SECRET') or ''
if not key or not secret:
    raise SystemExit('missing FANB credentials')
rows=[]
with candidate_csv.open('r', encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f): rows.append(r)
seen=set(); unique=[]
for r in rows:
    iid=str(r['num_iid']).strip()
    if iid and iid not in seen:
        seen.add(iid); unique.append(r)
log(f'CONTROLLED_RUN start candidates={len(rows)} unique={len(unique)} marker={start_marker}')
store=SQLiteItemStore('data/taobao_item_get.sqlite3')
config=ItemCrawlerConfig(key=key, secret=secret, num_iids=[], db_path='data/taobao_item_get.sqlite3', max_workers=1, lang='zh-CN', delay=0.2, timeout=60, retries=3, item_api='item_get')
fetched=failed=skipped=0
try:
    for idx,r in enumerate(unique,1):
        kw=r['keyword']; iid=r['num_iid']
        before=topup.successful_count(store.conn, kw)
        if before >= target:
            skipped += 1
            continue
        state=store.get_item_state(iid)
        status=state.get('status') if state else None
        last_error=str(state.get('last_error') or '') if state else ''
        if status=='success' or status=='not_found' or status=='blocked_5000_pro' or 'item-not-found' in last_error or 'error_code=2000' in last_error:
            skipped += 1
            continue
        store.mark_pending(iid)
        try:
            num_iid, result_status, payload = topup.crawl_one(config, iid)
        except topup.BillingAuthError as exc:
            store.mark_error(iid, exc)
            log(f'STOP billing_auth idx={idx} keyword={kw} iid={iid} error={exc}')
            raise SystemExit(2)
        if result_status=='success':
            store.save_item_detail(num_iid, payload)
            fetched += 1
        elif result_status=='blocked_5000_pro':
            store.mark_blocked_5000_pro(num_iid, payload)
            failed += 1
        elif result_status=='abandoned_503':
            store.mark_abandoned_503(num_iid, payload)
            failed += 1
        else:
            # Normalize not_found on the way in to reduce future paid retries.
            if 'error_code=2000' in str(payload) or 'item-not-found' in str(payload):
                store._upsert_state(num_iid, 'not_found', str(payload))
            else:
                store.mark_error(num_iid, payload)
            failed += 1
        if idx % 25 == 0 or result_status=='success':
            after=topup.successful_count(store.conn, kw)
            log(f'progress idx={idx}/{len(unique)} keyword={kw} iid={iid} status={result_status} kw_success={after} fetched={fetched} failed={failed} skipped={skipped}')
        time.sleep(0.2)
finally:
    store.close()
log(f'CONTROLLED_RUN finished fetched={fetched} failed={failed} skipped={skipped}')
