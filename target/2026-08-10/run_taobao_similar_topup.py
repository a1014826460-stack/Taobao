from __future__ import annotations
import argparse, json, os, sqlite3, sys, threading, time
from collections import OrderedDict, defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from src.taobao.direct.search import SearchCrawlerConfig, crawl_search, query_fingerprint
from src.taobao.direct.item import ItemCrawlerConfig, SQLiteItemStore, SearchItemSeed, _num_iid_from_search_item, _search_items_from_raw_page
from src.tools import topup_taobao_item_details as topup

ROOT=Path(__file__).resolve().parents[1]
SEARCH_DB=ROOT/'data'/'taobao_search.sqlite3'
DETAIL_DB=ROOT/'data'/'taobao_item_get.sqlite3'
OUTDIR=ROOT/'target'/'taobao_similar_topup_20260730'
TARGET=200
SORTS=['','_sale']
SIMILAR=OrderedDict([
 ('高潮液',['女性高潮液','高潮润滑液','催情高潮液','女用快感液','高潮快感液','女性催情液','女用催情液','情趣催情液','女性增敏液','敏感液']),
 ('快感液',['女性快感液','女用快感液','快感润滑液','催情快感液','女性催情液','女用催情液','情趣催情液','女性增敏液','敏感液','爱液']),
 ('延时喷剂',['男用延时喷剂','持久延时喷剂','延时液喷剂','房事延时喷剂']),
 ('飞机杯',['男用飞机杯','自慰杯','倒模飞机杯','成人飞机杯']),
 ('电动飞机杯',['自动飞机杯','电动自慰杯','智能飞机杯','震动飞机杯','全自动飞机杯','伸缩飞机杯','男用电动自慰器','自动自慰器','电动名器','互动飞机杯']),
 ('男用自慰器',['男士自慰器','男性自慰器','男用情趣用品','男用飞机杯']),
 ('跳蛋',['震动跳蛋','无线跳蛋','女用跳蛋','情趣跳蛋']),
 ('穿戴跳蛋',['可穿戴跳蛋','内裤跳蛋','穿戴震动跳蛋','女用穿戴跳蛋']),
 ('遥控跳蛋',['无线遥控跳蛋','手机遥控跳蛋','远程遥控跳蛋','情趣遥控跳蛋']),
 ('情趣按摩棒',['女用按摩棒','情趣震动棒','成人按摩棒','女性按摩棒']),
 ('震动棒',['女用震动棒','情趣震动棒','成人震动棒','按摩震动棒']),
 ('AV棒',['AV震动棒','AV按摩棒','女用AV棒','成人AV棒','女用震动棒','成人按摩棒','情趣按摩棒','震动按摩棒','女性按摩棒','自慰棒']),
 ('吸吮跳蛋',['吸吮震动棒','吮吸跳蛋','吸吮按摩器','女用吸吮器']),
 ('仿真阳具',['仿真男根','假阳具','仿真按摩棒','硅胶阳具','硅胶男根','成人阳具','女用阳具','仿真棒','后庭阳具','双头阳具']),
 ('肛塞',['后庭肛塞','震动肛塞','情趣肛塞','硅胶肛塞','后庭塞','女用肛塞','肛门塞','后庭按摩器','后庭按摩棒','肛门按摩器']),
 ('前列腺按摩器',['男用前列腺按摩器','前列腺震动按摩器','后庭按摩器','男士按摩器','男用后庭按摩器','前列腺肛塞','前列腺震动棒','男用肛塞','后庭震动棒','男士肛塞']),
 ('倒模',['倒模名器','女优倒模','飞机杯倒模','真人倒模','女优名器','成人倒模','男用倒模','硅胶倒模','名器倒模','实体倒模']),
 ('名器',['女优名器','倒模名器','男用名器','飞机杯名器','成人名器','日本名器','女神名器','倒模飞机杯','男用倒模','全自动名器']),
])
class BillingAuthError(RuntimeError): pass

def utc_now_iso(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def load_dotenv():
    p=ROOT/'.env'
    if p.exists():
        for raw in p.read_text(encoding='utf-8').splitlines():
            line=raw.strip()
            if line and not line.startswith('#') and '=' in line:
                k,_,v=line.partition('=')
                if k.strip() and k.strip() not in os.environ: os.environ[k.strip()]=v.strip().strip('"\'')
def is_billing(x):
    s=str(x); return 'error_code=4016' in s or '已欠费' in s
def successful_counts(conn):
    rows=conn.execute("""
        SELECT s.keyword, COUNT(DISTINCT s.num_iid) c
        FROM item_detail_sources s
        JOIN item_detail_state st ON st.num_iid=s.num_iid AND st.status='success'
        JOIN item_details d ON d.num_iid=s.num_iid AND TRIM(COALESCE(d.raw_json,''))<>''
        GROUP BY s.keyword
    """).fetchall()
    return {r[0]:int(r[1]) for r in rows}
def current_gaps():
    con=sqlite3.connect(DETAIL_DB)
    try: counts=successful_counts(con)
    finally: con.close()
    gaps=OrderedDict()
    for kw in SIMILAR:
        c=counts.get(kw,0)
        if c<TARGET: gaps[kw]=TARGET-c
    return gaps
def search_errors(cfg):
    fp=query_fingerprint(cfg); con=sqlite3.connect(SEARCH_DB)
    try: rows=con.execute("select page,last_error from search_state where query_fingerprint=? and status='error' order by page",(fp,)).fetchall()
    finally: con.close()
    return '\n'.join(f'page={p} {e}' for p,e in rows if e)
def run_searches(args,key,secret,gaps):
    OUTDIR.mkdir(parents=True,exist_ok=True)
    log_path=OUTDIR/f"similar_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    runs=[(kw,q,sort) for kw in gaps for q in SIMILAR[kw][:args.similar_per_keyword] for sort in SORTS[:args.sorts_per_keyword]]
    with log_path.open('w',encoding='utf-8') as log:
        log.write(f'start={utc_now_iso()} runs={len(runs)} max_pages={args.search_pages}\n')
        for i,(kw,q,sort) in enumerate(runs,1):
            cfg=SearchCrawlerConfig(key=key,secret=secret,query=q,db_path=str(SEARCH_DB),max_pages=args.search_pages,max_workers=args.search_workers,sort=sort,delay=args.search_delay,timeout=args.timeout,retries=args.search_retries,lang='zh-CN',cache='no')
            before=search_errors(cfg); res=crawl_search(cfg); err=search_errors(cfg)
            msg=f"SEARCH {i}/{len(runs)} original={kw} q={q} sort={sort!r} fetched={res.fetched_pages} skipped={res.skipped_pages} failed={res.failed_pages} saved_items={res.saved_items}"
            print(msg,flush=True); log.write(msg+'\n'); log.flush()
            if err and err!=before:
                log.write(err+'\n'); log.flush()
                if is_billing(err): raise BillingAuthError(f'4016 search original={kw} q={q}: {err}')
    return log_path
def load_similar_candidates(args,gaps):
    con=sqlite3.connect(SEARCH_DB); con.row_factory=sqlite3.Row
    try: rows=con.execute('select query_fingerprint,page,raw_json from search_pages order by query_fingerprint,page').fetchall()
    finally: con.close()
    source={q:kw for kw in gaps for q in SIMILAR[kw][:args.similar_per_keyword]}
    out=OrderedDict((kw,[]) for kw in gaps); seen=defaultdict(set)
    for row in rows:
        try: fp=json.loads(row['query_fingerprint'])
        except Exception: continue
        q=str(fp.get('q') or ''); sort=str(fp.get('sort') or '')
        if q not in source or sort not in SORTS[:args.sorts_per_keyword]: continue
        kw=source[q]
        for item in _search_items_from_raw_page(row['raw_json']):
            if not isinstance(item,dict): continue
            iid=_num_iid_from_search_item(item)
            if not iid or iid in seen[kw]: continue
            seen[kw].add(iid); out[kw].append(SearchItemSeed(kw,f'similar:{q}:{sort}',int(row['page']),iid))
    return out
def crawl_details(args,key,secret,gaps):
    OUTDIR.mkdir(parents=True,exist_ok=True)
    store=SQLiteItemStore(DETAIL_DB)
    cfg=ItemCrawlerConfig(key=key,secret=secret,num_iids=[],db_path=str(DETAIL_DB),max_workers=args.detail_workers,lang='zh-CN',delay=args.detail_delay,timeout=args.timeout,retries=args.detail_retries,item_api='item_get')
    log_path=OUTDIR/f"similar_detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    total_fetched=total_failed=total_submitted=0; stop=False
    try:
        candidates=load_similar_candidates(args,gaps)
        with log_path.open('w',encoding='utf-8') as log:
            log.write(f'start={utc_now_iso()} detail_limit={args.detail_limit}\n')
            last_request=0.0; throttle=threading.Lock()
            def worker(iid,forced):
                nonlocal last_request
                with throttle:
                    w=last_request+max(0.0,args.detail_delay)-time.monotonic()
                    if w>0: time.sleep(w)
                    last_request=time.monotonic()
                return topup.crawl_one(cfg,iid,forced)
            for kw,seeds in candidates.items():
                if stop or total_submitted>=args.detail_limit: break
                store.save_sources(seeds)
                before=topup.successful_count(store.conn,kw); need=max(0,TARGET-before)
                if need<=0:
                    msg=f'DETAIL keyword={kw} already={before} candidates={len(seeds)}'; print(msg,flush=True); log.write(msg+'\n'); continue
                fresh=[]; queued=[]; retryable=[]; retry_503=[]; retry_error=[]; local_seen=set()
                for seed in seeds:
                    if seed.num_iid in local_seen: continue
                    local_seen.add(seed.num_iid)
                    st=store.get_item_state(seed.num_iid); status=st.get('status') if st else None; le=str(st.get('last_error') or '') if st else ''
                    if is_billing(le) or status in topup.SKIP_STATUSES: continue
                    if status is None:
                        fresh.append((seed.num_iid,None))
                    elif status=='pending':
                        queued.append((seed.num_iid,None))
                    elif status=='retryable':
                        retryable.append((seed.num_iid,None))
                    elif status=='abandoned_503':
                        retry_503.append((seed.num_iid,None))
                    else:
                        retry_error.append((seed.num_iid,None))
                pending=(fresh+queued+retryable)
                if args.retry_503: pending += retry_503
                if args.retry_errors: pending += retry_error
                pending=pending[:need+args.detail_overfetch_per_keyword]
                msg=f'DETAIL_PLAN keyword={kw} before={before} need={need} candidates={len(seeds)} pending={len(pending)}'
                print(msg,flush=True); log.write(msg+'\n'); log.flush()
                fetched=failed=0; in_flight={}; it=iter(pending)
                with ThreadPoolExecutor(max_workers=args.detail_workers) as ex:
                    def submit():
                        nonlocal total_submitted
                        while before+fetched<TARGET and len(in_flight)<args.detail_workers and total_submitted<args.detail_limit:
                            try: iid,forced=next(it)
                            except StopIteration: break
                            store.mark_pending(iid); in_flight[ex.submit(worker,iid,forced)]=iid; total_submitted+=1
                    submit()
                    while in_flight and before+fetched<TARGET:
                        done,_=wait(set(in_flight),return_when=FIRST_COMPLETED)
                        for fut in done:
                            iid=in_flight.pop(fut)
                            try: num_iid,status,payload=fut.result()
                            except topup.BillingAuthError as exc:
                                stop=True; msg=f'STOP billing_auth keyword={kw} iid={iid} error={exc}'; print(msg,flush=True); log.write(msg+'\n'); break
                            if status=='success': store.save_item_detail(num_iid,payload); fetched+=1; total_fetched+=1
                            elif status=='blocked_5000_pro': store.mark_blocked_5000_pro(num_iid,payload); failed+=1; total_failed+=1
                            elif status=='abandoned_503': store.mark_abandoned_503(num_iid,payload); failed+=1; total_failed+=1
                            else: store.mark_error(num_iid,payload); failed+=1; total_failed+=1
                        if stop or total_submitted>=args.detail_limit: break
                        submit()
                    for fut,iid in list(in_flight.items()):
                        try: num_iid,status,payload=fut.result()
                        except topup.BillingAuthError as exc: stop=True; log.write(f'STOP billing_auth drain keyword={kw} iid={iid} error={exc}\n'); continue
                        if status=='success': store.save_item_detail(num_iid,payload); fetched+=1; total_fetched+=1
                        elif status=='blocked_5000_pro': store.mark_blocked_5000_pro(num_iid,payload); failed+=1; total_failed+=1
                        elif status=='abandoned_503': store.mark_abandoned_503(num_iid,payload); failed+=1; total_failed+=1
                        else: store.mark_error(num_iid,payload); failed+=1; total_failed+=1
                after=topup.successful_count(store.conn,kw)
                msg=f'DETAIL_DONE keyword={kw} before={before} after={after} fetched={fetched} failed={failed} submitted_total={total_submitted}'
                print(msg,flush=True); log.write(msg+'\n'); log.flush()
                if total_submitted>=args.detail_limit: log.write('DETAIL_LIMIT reached\n'); break
            log.write(f'finished fetched={total_fetched} failed={total_failed} submitted={total_submitted}\n')
    finally: store.close()
    return log_path,total_fetched,total_failed,total_submitted
def print_summary():
    con=sqlite3.connect(DETAIL_DB)
    try: counts=successful_counts(con)
    finally: con.close()
    total=gap_total=0
    for kw in SIMILAR:
        c=counts.get(kw,0); gap=max(0,TARGET-c); total+=c; gap_total+=gap; print(f'SUMMARY {kw} success={c} gap={gap}',flush=True)
    print(f'SUMMARY_TOTAL keyword_success={total} gap={gap_total}',flush=True)
def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--dry-run',action='store_true'); ap.add_argument('--skip-search',action='store_true'); ap.add_argument('--skip-detail',action='store_true')
    ap.add_argument('--similar-per-keyword',type=int,default=2); ap.add_argument('--sorts-per-keyword',type=int,default=2)
    ap.add_argument('--search-pages',type=int,default=3); ap.add_argument('--search-workers',type=int,default=2); ap.add_argument('--search-delay',type=float,default=0.25); ap.add_argument('--search-retries',type=int,default=1)
    ap.add_argument('--detail-limit',type=int,default=300); ap.add_argument('--detail-workers',type=int,default=3); ap.add_argument('--detail-delay',type=float,default=0.25); ap.add_argument('--detail-retries',type=int,default=1); ap.add_argument('--detail-overfetch-per-keyword',type=int,default=20); ap.add_argument('--retry-errors',action='store_true'); ap.add_argument('--retry-503',action='store_true')
    ap.add_argument('--timeout',type=float,default=60.0)
    args=ap.parse_args(argv); load_dotenv(); key=os.environ.get('FANB_API_KEY') or os.environ.get('KEY') or ''; secret=os.environ.get('FANB_API_SECRET') or os.environ.get('SECRET') or ''
    if not key or not secret: raise SystemExit('missing Fan-B credentials')
    gaps=current_gaps(); search_requests=len(gaps)*min(args.similar_per_keyword,4)*min(args.sorts_per_keyword,len(SORTS))*args.search_pages
    print(f'PLAN gap_keywords={len(gaps)} search_requests_max={search_requests} detail_requests_max={args.detail_limit}',flush=True)
    for kw,g in gaps.items(): print(f'GAP {kw} {g} similar={SIMILAR[kw][:args.similar_per_keyword]}',flush=True)
    if args.dry_run:
        cand=load_similar_candidates(args,gaps)
        for kw,seeds in cand.items(): print(f'DRY_CANDIDATES {kw} {len(seeds)}',flush=True)
        print_summary(); return 0
    try:
        if not args.skip_search: print(f'SEARCH_LOG {run_searches(args,key,secret,gaps)}',flush=True)
        if not args.skip_detail:
            log,fetched,failed,submitted=crawl_details(args,key,secret,gaps); print(f'DETAIL_LOG {log} fetched={fetched} failed={failed} submitted={submitted}',flush=True)
    except BillingAuthError as exc:
        print(f'STOP_BILLING_AUTH {exc}',flush=True); print_summary(); return 2
    print_summary(); return 0
if __name__=='__main__': raise SystemExit(main())
