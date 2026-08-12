from taobao.browser.human_behavior import DelayPolicy, humanize_page
import asyncio
class M:
    def __init__(self): self.wheels=[]
    async def move(self,*a,**k): pass
    async def wheel(self,*a): self.wheels.append(a)
class P:
    viewport_size={"width":800,"height":600}
    def __init__(self,h): self.h=h; self.mouse=M()
    async def evaluate(self,s):
        if self.h == "error": raise RuntimeError()
        return self.h
def test_unknown_height_skips_scroll():
    async def n(x): pass
    p=DelayPolicy(0,0,sleep_func=n); page=P("error")
    asyncio.run(humanize_page(page,p)); assert page.mouse.wheels == []
def test_wait_validation():
    import pytest
    p=DelayPolicy(1,2,sleep_func=lambda x: None)
    with pytest.raises(ValueError): asyncio.run(p.wait(-1))
    with pytest.raises(ValueError): asyncio.run(p.wait(3))
