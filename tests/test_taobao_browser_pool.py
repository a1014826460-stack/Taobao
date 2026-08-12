import pytest
from src.taobao.browser.browser_pool import BrowserPool
from src.taobao.browser.accounts import AccountRecord, CookieRecord

class FakePage:
    pass
class FakeContext:
    def __init__(self): self.cookies=[]; self.closed=False; self.pages=[]
    async def add_cookies(self,c): self.cookies.extend(c)
    async def new_page(self): p=FakePage(); self.pages.append(p); return p
    async def close(self): self.closed=True
class FakeBrowser:
    def __init__(self): self.contexts=[]; self.closed=False
    async def new_context(self, **kwargs):
        c=FakeContext(); self.contexts.append((c,kwargs)); return c
    async def close(self): self.closed=True
class Factory:
    def __init__(self): self.browsers=[]
    async def __call__(self, **kwargs):
        b=FakeBrowser(); self.browsers.append((b,kwargs)); return b

@pytest.mark.asyncio
async def test_pool_isolates_contexts_and_cookies():
    factory=Factory(); accounts=[AccountRecord('a','a.txt'), AccountRecord('b','b.txt')]
    pool=BrowserPool(accounts, browser_factory=factory, headless=True)
    a=await pool.start_account('a'); b=await pool.start_account('b')
    assert a.context is not b.context
    await a.install_cookies([CookieRecord('sid','A','.taobao.com')])
    await b.install_cookies([CookieRecord('sid','B','.taobao.com')])
    assert a.context.cookies[0]['value']=='A' and b.context.cookies[0]['value']=='B'
    assert factory.browsers[0][1]['headless'] is True
    await pool.close_all()
    assert a.context.closed and b.context.closed

@pytest.mark.asyncio
async def test_default_visible_and_stop_one_account():
    factory=Factory(); pool=BrowserPool([AccountRecord('a','a'),AccountRecord('b','b')], browser_factory=factory)
    a=await pool.start_account('a'); b=await pool.start_account('b')
    assert factory.browsers[0][1]['headless'] is False
    await pool.stop_account('a')
    assert a.context.closed
    assert not b.context.closed
    assert await pool.get('a') is None
