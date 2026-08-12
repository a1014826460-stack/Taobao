import csv, os, sqlite3, sys, time, threading, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from src.jd.direct.item import JDItemCrawlerConfig, SQLiteJDItemStore, fetch_jd_item_detail, parse_jd_item_response

candidate_csv=Path('target/jd_detail_19_keywords_20260729/existing_search_detail_candidates.csv')
log_path=Path('target/jd_detail_19_keywords_20260729/detail_run_existing.log')
marker_path=Path('target/jd_detail_19_keywords_20260729/detail_run_existing_since.txt')
marker='2026-07-29T14:10:00+00:00'
workers=4; delay=0.2

def log(msg):
    print(msg, flush=True)
    with log_path.open('a', encoding='utf-8') as f: f.write(msg+'\n')

# load env: prefer .env then password.env
for envfile in ['.env','password.env']:
    p=Path(envfile)
    if p.exists():
        for raw in p.read_text(encoding='utf-8').splitlines():
            line=raw.strip()
            if line and not line.startswith('#') and '=' in line:
                k,_,v=line.partition('='); os.environ.setdefault(k.strip().upper() if k.strip() in {'key','secret'} else k.strip(), v.strip().strip('"\''))
key=os.environ.get('FANB_API_KEY') or os.environ.get('KEY') or os.environ.get('key'.upper()) or ''
secret=os.environ.get('FANB_API_SECRET') or os.environ.get('SECRET') or os.environ.get('secret'.upper()) or ''
if not key or not secret: raise SystemExit('missing Fan-B credentials')
rows=[]
with candidate_csv.open('r', encoding='utf-8-sig', newline='') as f:
    rows=list(csv.DictReader(f))
seen=set(); unique=[]
for r in rows:
    iid=str(r['num_iid']).strip()
    if iid and iid not in seen:
        seen.add(iid); unique.append(r)
marker_path.write_text(marker+'\n', encoding='utf-8')
store=SQLiteJDItemStore('data/jd_item_details.sqlite3')
store.conn.executescript('''CREATE TABLE IF NOT EXISTS jd_item_sources (keyword TEXT NOT NULL, sort TEXT NOT NULL, page INTEGER NOT NULL, num_iid TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(keyword, sort, page, num_iid));''')
store.conn.commit()
config=JDItemCrawlerConfig(key=key, secret=secret, num_iids=[], db_path='data/jd_item_details.sqlite3', reset_items=False, cache='no', lang='zh-CN', delay=delay, timeout=30, retries=3)
last_request=0.0; throttle=threading.Lock(); stop=threading.Event()

def is_billing(e):
    t=str(e); return '4016' in t or '已欠费' in t or '欠费' in t

def worker(row):
    global last_request
    iid=row['num_iid']
    if stop.is_set(): return (row,'skipped_stop',None)
    with throttle:
        wait_for=last_request + delay - time.monotonic()
        if wait_for>0: time.sleep(wait_for)
        last_request=time.monotonic()
    try:
        resp=fetch_jd_item_detail(config, iid)
        parse_jd_item_response(resp)
        return (row,'success',resp)
    except Exception as exc:
        if is_billing(exc): stop.set(); return (row,'billing_auth',exc)
        return (row,'error',exc)

log(f'JD_DETAIL_EXISTING start candidates={len(rows)} unique={len(unique)} workers={workers} marker={marker}')
idx=0; in_flight={}; processed=fetched=failed=skipped=0
try:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        def should_skip(row):
            st=store.get_item_state(row['num_iid'])
            return bool(st and st.get('status')=='success')
        def submit_more():
            global idx, skipped
            while not stop.is_set() and len(in_flight)<workers and idx<len(unique):
                row=unique[idx]; idx+=1
                if should_skip(row):
                    globals()['skipped'] += 1
                    # still record source for existing success
                    with store.conn:
                        store.conn.execute('insert or ignore into jd_item_sources values (?,?,?,?,?)',(row['keyword'],row['sort'],int(row['page']),row['num_iid'],marker))
                    continue
                store.mark_pending(row['num_iid'])
                with store.conn:
                    store.conn.execute('insert or ignore into jd_item_sources values (?,?,?,?,?)',(row['keyword'],row['sort'],int(row['page']),row['num_iid'],marker))
                in_flight[ex.submit(worker,row)]=row
        submit_more()
        while in_flight:
            done,_=wait(in_flight.keys(), return_when=FIRST_COMPLETED)
            for fut in done:
                row=in_flight.pop(fut); processed+=1
                row,status,payload=fut.result(); iid=row['num_iid']
                if status=='success': store.save_item_detail(iid,payload); fetched+=1
                elif status=='billing_auth': store.mark_error(iid,payload); failed+=1; stop.set(); log(f'STOP billing_auth idx={idx} keyword={row["keyword"]} iid={iid} error={payload}')
                elif status=='skipped_stop': skipped+=1
                else: store.mark_error(iid,payload); failed+=1
                if processed%25==0 or status in {'success','billing_auth'}:
                    log(f'progress processed={processed} submitted={idx}/{len(unique)} keyword={row["keyword"]} iid={iid} status={status} fetched={fetched} failed={failed} skipped={skipped}')
            submit_more()
finally:
    store.close()
log(f'JD_DETAIL_EXISTING finished processed={processed} fetched={fetched} failed={failed} skipped={skipped} stopped={stop.is_set()}')
if stop.is_set(): raise SystemExit(2)
