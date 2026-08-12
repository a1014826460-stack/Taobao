import csv, os, sys, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from src.tools import topup_taobao_item_details as topup
from src.taobao.direct.item import ItemCrawlerConfig, SQLiteItemStore
keywords=topup.DEFAULT_KEYWORDS; target=200; workers=4; delay=0.2
candidate_csv=Path('target/taobao_detail_gap_20260729/controlled_candidates_remaining.csv')
run_log=Path('target/taobao_detail_gap_20260729/controlled_run_parallel.log')
marker='2026-07-29T10:23:00+00:00'

def log(msg):
    print(msg, flush=True)
    with run_log.open('a', encoding='utf-8') as f: f.write(msg+'\n')

if Path('.env').exists():
    for raw in Path('.env').read_text(encoding='utf-8').splitlines():
        line=raw.strip()
        if line and not line.startswith('#') and '=' in line:
            k,_,v=line.partition('='); os.environ.setdefault(k.strip(), v.strip().strip('"\''))
key=os.environ.get('FANB_API_KEY') or os.environ.get('KEY') or ''
secret=os.environ.get('FANB_API_SECRET') or os.environ.get('SECRET') or ''
if not key or not secret: raise SystemExit('missing FANB credentials')
rows=[]
with candidate_csv.open('r', encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f): rows.append(r)
seen=set(); unique=[]
for r in rows:
    iid=str(r['num_iid']).strip()
    if iid and iid not in seen: seen.add(iid); unique.append(r)
store=SQLiteItemStore('data/taobao_item_get.sqlite3')
config=ItemCrawlerConfig(key=key, secret=secret, num_iids=[], db_path='data/taobao_item_get.sqlite3', max_workers=workers, lang='zh-CN', delay=delay, timeout=60, retries=3, item_api='item_get')
last_request=0.0; throttle=threading.Lock(); stop=threading.Event()

def worker(row):
    global last_request
    iid=row['num_iid']
    if stop.is_set(): return (row,'skipped_stop',None)
    with throttle:
        wait_for=last_request + delay - time.monotonic()
        if wait_for>0: time.sleep(wait_for)
        last_request=time.monotonic()
    try:
        num_iid,status,payload=topup.crawl_one(config,iid)
        return (row,status,payload)
    except topup.BillingAuthError as exc:
        stop.set(); return (row,'billing_auth',exc)

log(f'CONTROLLED_PARALLEL start candidates={len(rows)} unique={len(unique)} workers={workers} marker={marker}')
fetched=failed=skipped=processed=0; idx=0; in_flight={}
try:
  with ThreadPoolExecutor(max_workers=workers) as ex:
    def should_skip(row):
        kw=row['keyword']; iid=row['num_iid']
        if topup.successful_count(store.conn, kw) >= target: return True
        st=store.get_item_state(iid); status=st.get('status') if st else None; err=str(st.get('last_error') or '') if st else ''
        return status in {'success','not_found','blocked_5000_pro'} or 'item-not-found' in err or 'error_code=2000' in err
    def submit_more():
        global idx, skipped
        nonlocal_vars=None
        while not stop.is_set() and len(in_flight)<workers and idx < len(unique):
            row=unique[idx]; idx+=1
            if should_skip(row):
                globals()['skipped'] += 1
                continue
            store.mark_pending(row['num_iid'])
            in_flight[ex.submit(worker,row)] = row
    submit_more()
    while in_flight:
        done,_=wait(in_flight.keys(), return_when=FIRST_COMPLETED)
        for fut in done:
            row=in_flight.pop(fut); kw=row['keyword']; iid=row['num_iid']
            row,status,payload=fut.result(); processed+=1
            if status=='success':
                store.save_item_detail(iid,payload); fetched+=1
            elif status=='billing_auth':
                store.mark_error(iid,payload); failed+=1; stop.set(); log(f'STOP billing_auth idx={idx} keyword={kw} iid={iid} error={payload}')
            elif status=='blocked_5000_pro':
                store.mark_blocked_5000_pro(iid,payload); failed+=1
            elif status=='abandoned_503':
                store.mark_abandoned_503(iid,payload); failed+=1
            elif status=='skipped_stop':
                skipped+=1
            else:
                if 'error_code=2000' in str(payload) or 'item-not-found' in str(payload): store._upsert_state(iid,'not_found',str(payload))
                else: store.mark_error(iid,payload)
                failed+=1
            if processed % 25 == 0 or status in {'success','billing_auth'}:
                log(f'progress processed={processed} submitted_index={idx}/{len(unique)} keyword={kw} iid={iid} status={status} kw_success={topup.successful_count(store.conn,kw)} fetched={fetched} failed={failed} skipped={skipped}')
        submit_more()
finally:
  store.close()
log(f'CONTROLLED_PARALLEL finished processed={processed} fetched={fetched} failed={failed} skipped={skipped} stopped={stop.is_set()}')
if stop.is_set(): raise SystemExit(2)
