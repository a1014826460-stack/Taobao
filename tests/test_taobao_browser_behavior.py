import asyncio
from taobao.browser.human_behavior import DelayPolicy, humanize_page
from taobao.browser.risk_control import classify_risk

class Mouse:
    def __init__(self): self.moves=[]; self.wheels=[]
    async def move(self,*a,**kw): self.moves.append((a,kw))
    async def wheel(self,*a): self.wheels.append(a)
class Page:
    viewport_size={"width":800,"height":600}
    def __init__(self,h): self.mouse=Mouse(); self.h=h
    async def evaluate(self,script): return self.h

def test_delay_bounds_seeded():
    p=DelayPolicy(10,30,seed=1)
    assert all(10<=p.sample()<=30 for _ in range(20))

def test_invalid_delay():
    import pytest
    with pytest.raises(ValueError): DelayPolicy(-1,2)
    with pytest.raises(ValueError): DelayPolicy(3,2)

def test_humanize_short_no_scroll():
    calls=[]
    async def nosleep(x): calls.append(x)
    p=DelayPolicy(0,0,sleep_func=nosleep)
    page=Page(500)
    asyncio.run(humanize_page(page,p))
    assert page.mouse.moves and not page.mouse.wheels

def test_humanize_tall_scrolls_visible():
    async def nosleep(x): pass
    p=DelayPolicy(0,0,seed=1,sleep_func=nosleep)
    page=Page(3000)
    asyncio.run(humanize_page(page,p))
    assert 1<=len(page.mouse.wheels)<=4

def test_risk_markers():
    assert classify_risk("https://x/login", "", "", 200)=="login_expired"
    assert classify_risk("", "安全验证", "滑块", 200)=="challenge"
    assert classify_risk("", "", "访问频繁", 200)=="rate_limited"
    assert classify_risk("", "", "", 403)=="forbidden"
    assert classify_risk("https://item.taobao.com", "商品", "正常", 200) is None
