import json
import pytest
from taobao.browser.crawler import BrowserCrawler, CrawlerConfig
from taobao.browser.repository import BrowserCrawlerRepository
from taobao.browser.accounts import AccountRecord
from taobao.browser.human_behavior import DelayPolicy

class Resp:
    def __init__(self, url, payload, rtype='xhr', status=200):
        self.url=url; self.status=status; self.request=type('R', (), {'method':'GET','resource_type':rtype})(); self._body=json.dumps(payload)
    def headers(self): return {'content-type':'application/json'}
    async def body(self): return self._body

class Page:
    def __init__(self, responses): self.handlers={}; self.responses=responses; self.url=''; self.mouse=type('M', (), {'move':lambda *a,**k:None,'wheel':lambda *a,**k:None})()
    def on(self, event, cb): self.handlers.setdefault(event, []).append(cb)
    def off(self,event,cb): self.handlers.get(event,[]).remove(cb)
    async def goto(self,url):
        self.url=url
        for r in self.responses.get(url,[]):
            for cb in list(self.handlers.get('response', [])): cb(r)
    async def wait_for_load_state(self,*a): pass
    async def evaluate(self,*a): return 500
    async def title(self): return 'ok'
    class _Loc:
        async def inner_text(self): return ''
    def locator(self,*a): return self._Loc()
    @property
    def viewport_size(self): return {'width':1000,'height':800}

class Browser:
    def __init__(self,p): self.page=p
class Pool:
    def __init__(self,p): self.accounts={'a':AccountRecord('a','x')}; self.b=Browser(p)
    async def start_account(self, aid): return type('AB', (), {'account_id':aid,'page':self.b.page})()
    async def stop_account(self, aid): pass

@pytest.mark.asyncio
async def test_search_and_detail_persist(tmp_path):
    repo=BrowserCrawlerRepository(tmp_path/'db.sqlite'); repo.upsert_account(AccountRecord('a','x'))
    search='https://s.taobao.com/search?q=phone&page=1'
    detail='https://item.taobao.com/item.htm?id=1'
    responses={search:[Resp(search, {'items':[{'itemId':'1','title':'Phone','price':'10','shop':'S'},{'itemId':'2','title':'Case','price':'2'}]})], detail:[Resp(detail, {'itemId':'1','title':'Phone','description':'d','sellerId':'s1'}), Resp(detail+'/comments', {'itemId':'1','comments':[{'commentId':'c1','content':'great'}]}), Resp(detail+'/seller', {'itemId':'1','sellerId':'s1','shopName':'S'})]}
    page=Page(responses); c=BrowserCrawler(repo, Pool(page), CrawlerConfig(platforms=('taobao',), page_limit=1, delay_policy=DelayPolicy(0,0)))
    await c.run_keywords(['phone'])
    assert repo.conn.execute('select count(*) from search_products').fetchone()[0]==2
    assert repo.conn.execute('select count(*) from crawl_tasks where task_type="detail"').fetchone()[0]==2
    assert repo.conn.execute('select count(*) from product_details').fetchone()[0]>=1
    assert repo.conn.execute('select count(*) from product_comments').fetchone()[0]>=1
    assert repo.conn.execute('select count(*) from seller_infos').fetchone()[0]>=1

@pytest.mark.asyncio
async def test_risk_pauses_account_and_requeues(tmp_path):
    repo=BrowserCrawlerRepository(tmp_path/'db.sqlite'); repo.upsert_account(AccountRecord('a','x')); repo.enqueue_keyword('x','taobao',1)
    class RiskPage(Page):
        async def title(self): return '安全验证 challenge'
    page=RiskPage({})
    c=BrowserCrawler(repo, Pool(page), CrawlerConfig(platforms=('taobao',), page_limit=1, delay_policy=DelayPolicy(0,0)))
    out=await c.run_pending_tasks(); assert out['paused_accounts']==1
    row=repo.conn.execute('select status from crawl_tasks').fetchone(); assert row['status']=='pending'
    assert repo.available_accounts()==[]

@pytest.mark.asyncio
async def test_status_risk_detected_when_body_denied(tmp_path):
    repo=BrowserCrawlerRepository(tmp_path/'db.sqlite'); repo.upsert_account(AccountRecord('a','x')); repo.enqueue_keyword('x','taobao',1)
    class Denied(Resp):
        async def body(self): raise RuntimeError('denied')
    url='https://s.taobao.com/search?q=x&page=1'
    page=Page({url:[Denied(url, {}, status=403)]})
    c=BrowserCrawler(repo, Pool(page), CrawlerConfig(platforms=('taobao',), page_limit=1, delay_policy=DelayPolicy(0,0)))
    out=await c.run_pending_tasks(); assert out['paused_accounts']==1

@pytest.mark.asyncio
async def test_url_only_item_generates_detail(tmp_path):
    repo=BrowserCrawlerRepository(tmp_path/'db.sqlite'); repo.upsert_account(AccountRecord('a','x'))
    url='https://s.taobao.com/search?q=x&page=1'; detail_url='https://item.taobao.com/item/abc'
    page=Page({url:[Resp(url, {'items':[{'url':detail_url}]})]})
    c=BrowserCrawler(repo, Pool(page), CrawlerConfig(platforms=('taobao',), page_limit=1, delay_policy=DelayPolicy(0,0)))
    await c.run_keywords(['x'])
    assert repo.conn.execute('select count(*) from crawl_tasks where task_type="detail"').fetchone()[0]==1


@pytest.mark.asyncio
async def test_running_tasks_recovered_before_claim(tmp_path):
 repo=BrowserCrawlerRepository(tmp_path/'db.sqlite'); repo.upsert_account(AccountRecord('a','x')); ids=repo.enqueue_keyword('x','taobao',1); repo.conn.execute("update crawl_tasks set status='running'")
 page=Page({})
 c=BrowserCrawler(repo, Pool(page), CrawlerConfig(platforms=('taobao',), page_limit=1, delay_policy=DelayPolicy(0,0)))
 await c.run_pending_tasks(); assert repo.conn.execute('select status from crawl_tasks').fetchone()['status'] in ('success','failed','pending')

@pytest.mark.asyncio
async def test_search_only_keeps_detail_pending(tmp_path):
 repo=BrowserCrawlerRepository(tmp_path/'db.sqlite'); repo.upsert_account(AccountRecord('a','x')); repo.enqueue_detail('taobao','1')
 c=BrowserCrawler(repo, Pool(Page({})), CrawlerConfig(search_only=True, delay_policy=DelayPolicy(0,0)))
 await c.run_pending_tasks(); assert repo.conn.execute("select status from crawl_tasks where task_type='detail'").fetchone()['status']=='pending'

@pytest.mark.asyncio
async def test_search_ignores_nested_bogus_ids(tmp_path):
 repo=BrowserCrawlerRepository(tmp_path/'db.sqlite'); repo.upsert_account(AccountRecord('a','x'))
 url='https://s.taobao.com/search?q=x&page=1'; payload={'items':[{'itemId':'1','title':'A'}], 'metadata': {'id':'999','title':'bogus'}}
 c=BrowserCrawler(repo, Pool(Page({url:[Resp(url,payload)]})), CrawlerConfig(platforms=('taobao',), page_limit=1, delay_policy=DelayPolicy(0,0)))
 await c.run_keywords(['x']); rows=repo.conn.execute('select item_id from search_products').fetchall(); assert [r['item_id'] for r in rows]==['1']
