from taobao.browser.human_behavior import DelayPolicy, humanize_page
import asyncio
class M:
 def __init__(self): self.wheels=[]
 async def move(self,*a,**k): pass
 async def wheel(self,*a): self.wheels.append(a)
class P:
 viewport_size={'width':800,'height':600}
 def __init__(self,h): self.h=h; self.mouse=M()
 async def evaluate(self,s): return self.h
def test_non_numeric_height_skips():
 async def n(x): pass
 for h in ('oops', float('nan'), float('inf')):
  p=P(h); asyncio.run(humanize_page(p,DelayPolicy(0,0,sleep_func=n))); assert not p.mouse.wheels
