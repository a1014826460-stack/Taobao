from __future__ import annotations
import json, sqlite3, subprocess, sys
from datetime import datetime
from pathlib import Path

KEYWORDS=["润滑液","高潮液","快感液","延时喷剂","飞机杯","电动飞机杯","男用自慰器","跳蛋","穿戴跳蛋","遥控跳蛋","情趣按摩棒","震动棒","AV棒","吸吮跳蛋","仿真阳具","肛塞","前列腺按摩器","倒模","名器"]
FALLBACK_SORTS=["_review","_bid","_new","bid"]
DB="data/jd_search.sqlite3"
TARGET_PAGES=30
LOG=Path('target')/f"jd_search_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

def success_pages_by_kw():
    conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
    out={kw:set() for kw in KEYWORDS}
    for r in conn.execute('select query_fingerprint,page from jd_search_pages'):
        fp=json.loads(r['query_fingerprint']); kw=fp.get('q') or ''; sort=fp.get('sort') or ''
        if kw in out:
            out[kw].add((sort, int(r['page'])))
    conn.close(); return out

LOG.parent.mkdir(exist_ok=True)
with LOG.open('w',encoding='utf-8') as log:
    for sort in FALLBACK_SORTS:
        pages=success_pages_by_kw()
        need=[kw for kw in KEYWORDS if len(pages[kw]) < TARGET_PAGES]
        if not need:
            break
        for kw in need:
            current=len(success_pages_by_kw()[kw])
            if current >= TARGET_PAGES:
                continue
            cmd=[sys.executable,'-m','src.jd.direct.search','--q',kw,'--sort',sort,'--max-pages','20','--workers','6','--delay','0.05','--timeout','45','--retries','3','--db',DB]
            print(f'RUN fallback keyword={kw} sort={sort} current_pages={current}', flush=True)
            log.write(f"\n=== RUN keyword={kw} sort={sort} current_pages={current} ===\n")
            proc=subprocess.run(cmd,cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True)
            log.write(proc.stdout); log.write(proc.stderr); log.write(f"\nexit={proc.returncode}\n"); log.flush()
            print(f'DONE fallback keyword={kw} sort={sort} exit={proc.returncode}', flush=True)
print(LOG)
