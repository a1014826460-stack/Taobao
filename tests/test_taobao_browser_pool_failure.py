import pytest
from src.taobao.browser.browser_pool import BrowserPool
from src.taobao.browser.accounts import AccountRecord

class Context:
    def __init__(self, fail_page=False): self.closed=False; self.fail_page=fail_page
    async def new_page(self):
        if self.fail_page: raise RuntimeError('page failed')
        return object()
    async def close(self): self.closed=True
class Browser:
    def __init__(self, fail_context=False, fail_page=False): self.closed=False; self.fail_context=fail_context; self.fail_page=fail_page; self.context=None
    async def new_context(self, **kwargs):
        if self.fail_context: raise RuntimeError('context failed')
        self.context=Context(self.fail_page); return self.context
    async def close(self): self.closed=True
@pytest.mark.asyncio
async def test_context_failure_closes_browser():
    b=Browser(fail_context=True)
    async def factory(**kwargs): return b
    pool=BrowserPool([AccountRecord('a','a')], browser_factory=factory)
    with pytest.raises(RuntimeError): await pool.start_account('a')
    assert b.closed and not pool.instances
@pytest.mark.asyncio
async def test_page_failure_closes_context_and_browser():
    b=Browser(fail_page=True)
    async def factory(**kwargs): return b
    pool=BrowserPool([AccountRecord('a','a')], browser_factory=factory)
    with pytest.raises(RuntimeError): await pool.start_account('a')
    assert b.closed and b.context.closed and not pool.instances
