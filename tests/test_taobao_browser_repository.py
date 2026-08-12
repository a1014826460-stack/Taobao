import json
from src.taobao.browser.repository import BrowserCrawlerRepository
from src.taobao.browser.accounts import AccountRecord

def test_platform_unique_and_idempotent(tmp_path):
 r=BrowserCrawlerRepository(tmp_path/'x.db'); assert len(r.enqueue_keyword('k','taobao'))==3; assert len(r.enqueue_keyword('k','tmall'))==3

def test_pause_requeues_and_rejects(tmp_path):
 r=BrowserCrawlerRepository(tmp_path/'x.db'); r.upsert_account(AccountRecord('a','x')); ids=r.enqueue_keyword('k','taobao',1); assert r.claim_next_task('a','9999'); r.pause_account('a','bad'); assert r.claim_next_task('a','9999') is None

def test_upsert_account_preserves_pause(tmp_path):
 r=BrowserCrawlerRepository(tmp_path/'x.db'); r.upsert_account(AccountRecord('a','x')); r.pause_account('a','bad'); r.upsert_account(AccountRecord('a','x')); assert r.available_accounts()==[]

def test_network_redaction(tmp_path):
 r=BrowserCrawlerRepository(tmp_path/'x.db'); r.save_network_record({'url':'https://x/?token=secret','response_headers':{'Cookie':'abc','X':'ok'},'response_body':'body'}); row=r.conn.execute('select * from network_records').fetchone(); assert 'secret' not in row['url'] and 'abc' not in row['response_headers_json']
