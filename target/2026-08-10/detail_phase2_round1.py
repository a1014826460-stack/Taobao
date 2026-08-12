import csv, os, sqlite3, threading, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from pathlib import Path

from src.jd.direct.item import JDItemCrawlerConfig, SQLiteJDItemStore, fetch_jd_item_detail, parse_jd_item_response

KEYWORDS = ['电动飞机杯','穿戴跳蛋','吸吮跳蛋','遥控跳蛋','AV棒']
SORTS = ['', '_sale', '_review', '_new']
PER_KEYWORD_LIMIT = 260
OUTDIR = Path('target/jd_detail_19_keywords_20260729')
OUTDIR.mkdir(parents=True, exist_ok=True)
CANDIDATE_CSV = OUTDIR / 'phase2_round1_detail_candidates.csv'
LOG = OUTDIR / 'detail_run_phase2_round1.log'
MARKER = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
DB_SEARCH = 'data/jd_search.sqlite3'
DB_DETAIL = 'data/jd_item_details.sqlite3'
WORKERS = 4
DELAY = 0.2

# load env
for envfile in ['.env','password.env']:
    p = Path(envfile)
    if p.exists():
        for raw in p.read_text(encoding='utf-8').splitlines():
            line = raw.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                name = k.strip()
                value = v.strip().strip('"\'')
                if name and name not in os.environ:
                    os.environ[name] = value
key = os.environ.get('FANB_API_KEY') or os.environ.get('KEY') or ''
secret = os.environ.get('FANB_API_SECRET') or os.environ.get('SECRET') or ''
if not key or not secret:
    raise SystemExit('missing Fan-B credentials')

search = sqlite3.connect(DB_SEARCH)
search.row_factory = sqlite3.Row
search.execute(f"ATTACH DATABASE '{DB_DETAIL}' AS itemdb")
rows = []
for kw in KEYWORDS:
    seen = set()
    picked = 0
    for r in search.execute('''
        SELECT json_extract(s.query_fingerprint,'$.q') keyword,
               COALESCE(json_extract(s.query_fingerprint,'$.sort'),'') sort,
               s.first_seen_page page,
               s.num_iid,
               s.title
        FROM jd_search_items s
        LEFT JOIN itemdb.jd_item_state st ON st.num_iid=s.num_iid
        WHERE json_extract(s.query_fingerprint,'$.q')=?
          AND COALESCE(json_extract(s.query_fingerprint,'$.sort'),'') IN ('','_sale','_review','_new')
          AND st.num_iid IS NULL
        ORDER BY CASE COALESCE(json_extract(s.query_fingerprint,'$.sort'),'')
                   WHEN '' THEN 0 WHEN '_sale' THEN 1 WHEN '_review' THEN 2 WHEN '_new' THEN 3 ELSE 9 END,
                 s.first_seen_page,
                 s.num_iid
    ''', (kw,)):
        iid = str(r['num_iid']).strip()
        if not iid or iid in seen:
            continue
        seen.add(iid)
        rows.append({
            'keyword': kw,
            'sort': r['sort'] or '',
            'page': int(r['page']),
            'num_iid': iid,
            'title': r['title'] or '',
        })
        picked += 1
        if picked >= PER_KEYWORD_LIMIT:
            break
search.close()

with CANDIDATE_CSV.open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['keyword','sort','page','num_iid','title'])
    writer.writeheader()
    writer.writerows(rows)

by_iid = defaultdict(list)
for row in rows:
    by_iid[row['num_iid']].append(row)
unique_rows = [{'num_iid': iid, 'sources': sources} for iid, sources in by_iid.items()]

store = SQLiteJDItemStore(DB_DETAIL)
store.conn.executescript('''
CREATE TABLE IF NOT EXISTS jd_item_sources (
  keyword TEXT NOT NULL,
  sort TEXT NOT NULL,
  page INTEGER NOT NULL,
  num_iid TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(keyword, sort, page, num_iid)
);
''')
store.conn.commit()
config = JDItemCrawlerConfig(key=key, secret=secret, num_iids=[], db_path=DB_DETAIL, reset_items=False, cache='no', lang='zh-CN', delay=DELAY, timeout=30, retries=3)
last_request = 0.0
throttle = threading.Lock()
stop = threading.Event()


def log(msg):
    print(msg, flush=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(msg + '\n')


def is_billing(e):
    t = str(e)
    return '4016' in t or '欠费' in t or '已欠费' in t or 'auth' in t.lower() or '认证' in t


def worker(bundle):
    global last_request
    iid = bundle['num_iid']
    if stop.is_set():
        return bundle, 'skipped_stop', None
    with throttle:
        wait_for = last_request + DELAY - time.monotonic()
        if wait_for > 0:
            time.sleep(wait_for)
        last_request = time.monotonic()
    try:
        resp = fetch_jd_item_detail(config, iid)
        parse_jd_item_response(resp)
        return bundle, 'success', resp
    except Exception as exc:
        if is_billing(exc):
            stop.set()
            return bundle, 'billing_auth', exc
        return bundle, 'error', exc

log(f'JD_DETAIL_PHASE2_ROUND1 start source_rows={len(rows)} unique_iids={len(unique_rows)} marker={MARKER} workers={WORKERS}')
idx = 0
processed = fetched = failed = skipped = 0
in_flight = {}
try:
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        def submit_more():
            global idx, skipped
            while not stop.is_set() and len(in_flight) < WORKERS and idx < len(unique_rows):
                bundle = unique_rows[idx]
                idx += 1
                iid = bundle['num_iid']
                with store.conn:
                    for src in bundle['sources']:
                        store.conn.execute(
                            'INSERT OR IGNORE INTO jd_item_sources(keyword,sort,page,num_iid,created_at) VALUES (?,?,?,?,?)',
                            (src['keyword'], src['sort'], int(src['page']), iid, MARKER)
                        )
                st = store.get_item_state(iid)
                if st and st.get('status') == 'success':
                    skipped += 1
                    continue
                store.mark_pending(iid)
                in_flight[ex.submit(worker, bundle)] = bundle
        submit_more()
        while in_flight:
            done, _ = wait(in_flight.keys(), return_when=FIRST_COMPLETED)
            for fut in done:
                bundle = in_flight.pop(fut)
                processed += 1
                bundle, status, payload = fut.result()
                iid = bundle['num_iid']
                if status == 'success':
                    store.save_item_detail(iid, payload)
                    fetched += 1
                elif status == 'billing_auth':
                    store.mark_error(iid, payload)
                    failed += 1
                    stop.set()
                    log(f'STOP billing_auth idx={idx} iid={iid} error={payload}')
                elif status == 'skipped_stop':
                    skipped += 1
                else:
                    store.mark_error(iid, payload)
                    failed += 1
                if processed % 25 == 0 or status in {'success','billing_auth'}:
                    kws = ','.join(sorted({src['keyword'] for src in bundle['sources']}))
                    log(f'progress processed={processed} submitted={idx}/{len(unique_rows)} iid={iid} keywords={kws} status={status} fetched={fetched} failed={failed} skipped={skipped}')
            submit_more()
finally:
    store.close()
log(f'JD_DETAIL_PHASE2_ROUND1 finished processed={processed} fetched={fetched} failed={failed} skipped={skipped} stopped={stop.is_set()}')
if stop.is_set():
    raise SystemExit(2)
