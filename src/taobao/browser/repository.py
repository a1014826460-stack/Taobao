from __future__ import annotations
import json, sqlite3, uuid, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .accounts import AccountRecord


def _now(): return datetime.now(timezone.utc).isoformat()
def _json(v): return json.dumps(v, ensure_ascii=False, sort_keys=True) if not isinstance(v,str) else v

class BrowserCrawlerRepository:
    def __init__(self, db_path: str|Path):
        self.db_path=Path(db_path); self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn=sqlite3.connect(str(self.db_path), timeout=30, isolation_level=None)
        self.conn.row_factory=sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON"); self.conn.execute("PRAGMA journal_mode=WAL"); self.conn.execute("PRAGMA busy_timeout=30000")
        self._schema()
    def close(self): self.conn.close()
    def _schema(self):
        self.conn.executescript('''
CREATE TABLE IF NOT EXISTS crawl_runs (run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, input_source TEXT NOT NULL, options_json TEXT NOT NULL, summary_json TEXT);
CREATE TABLE IF NOT EXISTS accounts (account_id TEXT PRIMARY KEY, cookie_source TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', pause_reason TEXT, last_used_at TEXT, success_count INTEGER NOT NULL DEFAULT 0, failure_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS crawl_tasks (task_id TEXT PRIMARY KEY, task_type TEXT NOT NULL CHECK(task_type IN ('keyword','detail')), keyword TEXT, item_id TEXT, platform TEXT, page_no INTEGER, source_url TEXT, status TEXT NOT NULL DEFAULT 'pending', account_id TEXT, attempts INTEGER NOT NULL DEFAULT 0, error TEXT, next_run_at TEXT, run_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(account_id) REFERENCES accounts(account_id), FOREIGN KEY(run_id) REFERENCES crawl_runs(run_id), UNIQUE(task_type,platform,keyword,page_no), UNIQUE(task_type,platform,item_id));
CREATE INDEX IF NOT EXISTS idx_tasks_status_next ON crawl_tasks(status,next_run_at);
CREATE INDEX IF NOT EXISTS idx_tasks_account ON crawl_tasks(account_id,status);
CREATE TABLE IF NOT EXISTS network_records (record_id TEXT PRIMARY KEY, run_id TEXT, account_id TEXT, page_type TEXT, url TEXT, method TEXT, status_code INTEGER, resource_type TEXT, response_headers_json TEXT, response_body TEXT, body_sha256 TEXT, captured_at TEXT, FOREIGN KEY(run_id) REFERENCES crawl_runs(run_id), FOREIGN KEY(account_id) REFERENCES accounts(account_id));
CREATE TABLE IF NOT EXISTS search_products (platform TEXT NOT NULL, keyword TEXT NOT NULL, page_no INTEGER NOT NULL, item_id TEXT NOT NULL, title TEXT, price TEXT, sales TEXT, shop TEXT, url TEXT, raw_json TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(platform,keyword,page_no,item_id));
CREATE TABLE IF NOT EXISTS product_details (platform TEXT NOT NULL, item_id TEXT NOT NULL, title TEXT, description_json TEXT, sku_json TEXT, images_json TEXT, raw_json TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(platform,item_id));
CREATE TABLE IF NOT EXISTS product_comments (platform TEXT NOT NULL, item_id TEXT NOT NULL, comment_id TEXT NOT NULL, rating TEXT, content TEXT, author_redacted TEXT, raw_json TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(platform,item_id,comment_id));
CREATE TABLE IF NOT EXISTS seller_infos (platform TEXT NOT NULL, item_id TEXT NOT NULL, seller_id TEXT, shop_name TEXT, level TEXT, ratings_json TEXT, raw_json TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(platform,item_id));
''')
    def create_run(self,input_source,options):
        rid=str(uuid.uuid4()); self.conn.execute('INSERT INTO crawl_runs VALUES (?,?,?,?,?,?)',(rid,_now(),None,input_source,_json(options),None)); return rid
    def finish_run(self,run_id,summary): self.conn.execute('UPDATE crawl_runs SET finished_at=?,summary_json=? WHERE run_id=?',(_now(),_json(summary),run_id))
    def upsert_account(self,account:AccountRecord):
        t=_now(); status='available' if account.status=='active' else account.status
        self.conn.execute('''INSERT INTO accounts(account_id,cookie_source,status,pause_reason,created_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(account_id) DO UPDATE SET cookie_source=excluded.cookie_source,status=CASE WHEN accounts.status IN ('paused','expired') THEN accounts.status ELSE excluded.status END,pause_reason=CASE WHEN accounts.status IN ('paused','expired') THEN accounts.pause_reason ELSE excluded.pause_reason END,updated_at=excluded.updated_at''',(account.account_id,account.cookie_source,status,account.pause_reason,t,t))
    def pause_account(self,account_id,reason):
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            self.conn.execute("UPDATE accounts SET status='paused',pause_reason=?,updated_at=? WHERE account_id=?",(reason,_now(),account_id))
            self.conn.execute("UPDATE crawl_tasks SET status='pending',account_id=NULL,error=?,updated_at=? WHERE account_id=? AND status='running'",(reason,_now(),account_id))
            self.conn.commit()
        except Exception:
            self.conn.rollback(); raise
    def available_accounts(self): return [dict(r) for r in self.conn.execute("SELECT * FROM accounts WHERE status IN ('active','available') ORDER BY COALESCE(last_used_at,'')").fetchall()]
    def enqueue_keyword(self,keyword,platform,page_limit=3,run_id=None):
        ids=[]
        for p in range(1,page_limit+1):
            tid=str(uuid.uuid4()); t=_now()
            self.conn.execute('''INSERT INTO crawl_tasks(task_id,task_type,keyword,platform,page_no,status,next_run_at,run_id,created_at,updated_at) VALUES(?,?,?,?,?,"pending",?,?,?,?) ON CONFLICT(task_type,platform,keyword,page_no) DO UPDATE SET run_id=COALESCE(excluded.run_id,crawl_tasks.run_id),updated_at=excluded.updated_at''',(tid,'keyword',keyword,platform,p,t,run_id,t,t))
            row=self.conn.execute("SELECT task_id FROM crawl_tasks WHERE task_type='keyword' AND platform=? AND keyword=? AND page_no=?",(platform,keyword,p)).fetchone(); ids.append(row['task_id'])
        return ids
    def enqueue_detail(self,platform,item_id,source_url=None,run_id=None):
        tid=str(uuid.uuid4()); t=_now(); self.conn.execute('''INSERT INTO crawl_tasks(task_id,task_type,item_id,platform,source_url,status,next_run_at,run_id,created_at,updated_at) VALUES(?,?, ?,?,?,"pending",?,?,?,?) ON CONFLICT(task_type,platform,item_id) DO UPDATE SET source_url=COALESCE(excluded.source_url,crawl_tasks.source_url),run_id=COALESCE(excluded.run_id,crawl_tasks.run_id),updated_at=excluded.updated_at''',(tid,'detail',item_id,platform,source_url,t,run_id,t,t)); return self.conn.execute("SELECT task_id FROM crawl_tasks WHERE task_type='detail' AND platform=? AND item_id=?",(platform,item_id)).fetchone()['task_id']
    def claim_next_task(self,account_id,now):
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            ok=self.conn.execute("SELECT 1 FROM accounts WHERE account_id=? AND status IN ('active','available')",(account_id,)).fetchone()
            if not ok: self.conn.rollback(); return None
            row=self.conn.execute("SELECT * FROM crawl_tasks WHERE status='pending' AND (next_run_at IS NULL OR next_run_at<=?) ORDER BY created_at LIMIT 1",(now,)).fetchone()
            if not row: self.conn.rollback(); return None
            t=_now(); cur=self.conn.execute("UPDATE crawl_tasks SET status='running',account_id=?,attempts=attempts+1,updated_at=? WHERE task_id=? AND status='pending'",(account_id,t,row['task_id']));
            if cur.rowcount != 1: self.conn.rollback(); return None
            self.conn.execute('UPDATE accounts SET last_used_at=?,updated_at=? WHERE account_id=?',(t,t,account_id)); result=dict(self.conn.execute('SELECT * FROM crawl_tasks WHERE task_id=?',(row['task_id'],)).fetchone()); self.conn.commit(); return result
        except Exception:
            self.conn.rollback(); raise
    def complete_task(self,task_id): self.conn.execute('UPDATE crawl_tasks SET status="success",error=NULL,updated_at=? WHERE task_id=?',(_now(),task_id))
    def fail_task(self,task_id,error,retry_at=None):
        status = "pending" if retry_at is not None else "failed"
        self.conn.execute("UPDATE crawl_tasks SET status=?,error=?,next_run_at=?,updated_at=? WHERE task_id=?",(status,error,retry_at,_now(),task_id))
    def pause_task(self,task_id,error): self.conn.execute('UPDATE crawl_tasks SET status="paused",error=?,updated_at=? WHERE task_id=?',(error,_now(),task_id))
    def recover_running_tasks(self):
        cur=self.conn.execute("UPDATE crawl_tasks SET status='pending',account_id=NULL,updated_at=? WHERE status='running'",(_now(),)); return cur.rowcount
    def save_network_record(self,record):
        r=dict(record); rid=r.get('record_id') or str(uuid.uuid4()); url=re.sub(r'([?&](?:token|sign))=[^&]*',r'\1=<redacted>',r.get('url') or '',flags=re.I)
        h=r.get('response_headers',r.get('response_headers_json',{}));
        if isinstance(h,str):
            try: h=json.loads(h)
            except Exception: h={}
        h={k:('<redacted>' if re.search(r'cookie|authorization|token|set-cookie',k,re.I) else v) for k,v in (h or {}).items()}
        def scrub(v):
            if isinstance(v,dict): return {k:('<redacted>' if re.search(r'cookie|set.cookie|authorization|token|sign',k,re.I) else scrub(x)) for k,x in v.items()}
            if isinstance(v,list): return [scrub(x) for x in v]
            return v
        body=r.get('response_body');
        try: body=_json(scrub(json.loads(body))) if isinstance(body,str) else _json(scrub(body))
        except Exception: body=body
        self.conn.execute('''INSERT INTO network_records(record_id,run_id,account_id,page_type,url,method,status_code,resource_type,response_headers_json,response_body,body_sha256,captured_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(record_id) DO UPDATE SET run_id=COALESCE(excluded.run_id,network_records.run_id),account_id=COALESCE(excluded.account_id,network_records.account_id),page_type=COALESCE(excluded.page_type,network_records.page_type),url=COALESCE(excluded.url,network_records.url),method=COALESCE(excluded.method,network_records.method),status_code=COALESCE(excluded.status_code,network_records.status_code),resource_type=COALESCE(excluded.resource_type,network_records.resource_type),response_headers_json=COALESCE(excluded.response_headers_json,network_records.response_headers_json),response_body=COALESCE(excluded.response_body,network_records.response_body),body_sha256=COALESCE(excluded.body_sha256,network_records.body_sha256),captured_at=COALESCE(excluded.captured_at,network_records.captured_at)''',(rid,r.get('run_id'),r.get('account_id'),r.get('page_type'),url,r.get('method'),r.get('status_code'),r.get('resource_type'),_json(h),body,r.get('body_sha256'),r.get('captured_at') or _now()))
    def upsert_search_product(self,r):
        self.conn.execute('''INSERT INTO search_products(platform,keyword,page_no,item_id,title,price,sales,shop,url,raw_json,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(platform,keyword,page_no,item_id) DO UPDATE SET title=excluded.title,price=excluded.price,sales=excluded.sales,shop=excluded.shop,url=excluded.url,raw_json=excluded.raw_json,updated_at=excluded.updated_at''',(r['platform'],r['keyword'],r['page_no'],r['item_id'],r.get('title'),r.get('price'),r.get('sales'),r.get('shop'),r.get('url'),_json(r.get('raw_json',r)),_now()))
    def upsert_product_detail(self,r): self.conn.execute('''INSERT INTO product_details VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(platform,item_id) DO UPDATE SET title=excluded.title,description_json=excluded.description_json,sku_json=excluded.sku_json,images_json=excluded.images_json,raw_json=excluded.raw_json,updated_at=excluded.updated_at''',(r['platform'],r['item_id'],r.get('title'),_json(r.get('description',r.get('description_json'))),_json(r.get('sku',r.get('sku_json'))),_json(r.get('images',r.get('images_json'))),_json(r.get('raw_json',r)),_now()))
    def upsert_comment(self,r): self.conn.execute('''INSERT INTO product_comments VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(platform,item_id,comment_id) DO UPDATE SET rating=excluded.rating,content=excluded.content,author_redacted=excluded.author_redacted,raw_json=excluded.raw_json,updated_at=excluded.updated_at''',(r['platform'],r['item_id'],r['comment_id'],r.get('rating'),r.get('content'),r.get('author_redacted'),_json(r.get('raw_json',r)),_now()))
    def upsert_seller(self,r): self.conn.execute('''INSERT INTO seller_infos VALUES(?,?,?,?,?,?,?) ON CONFLICT(platform,item_id) DO UPDATE SET seller_id=excluded.seller_id,shop_name=excluded.shop_name,level=excluded.level,ratings_json=excluded.ratings_json,raw_json=excluded.raw_json,updated_at=excluded.updated_at''',(r['platform'],r['item_id'],r.get('seller_id'),r.get('shop_name'),r.get('level'),_json(r.get('ratings',r.get('ratings_json'))),_json(r.get('raw_json',r)),_now()))

