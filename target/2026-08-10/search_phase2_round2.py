import sqlite3, subprocess, sys
from datetime import datetime
from pathlib import Path

KEYWORDS = ['男用自慰器','仿真阳具','快感液','情趣按摩棒','飞机杯','延时喷剂']
SORTS = ['', '_sale', '_review', '_new']
DB = 'data/jd_search.sqlite3'
ROOT = Path.cwd()
OUTDIR = ROOT / 'target' / 'jd_detail_19_keywords_20260729'
OUTDIR.mkdir(parents=True, exist_ok=True)
LOG = OUTDIR / 'search_phase2_round2.log'
MARK = datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

def check_4016_since(conn, since):
    row = conn.execute(
        """
        SELECT page, last_error, updated_at
        FROM jd_search_state
        WHERE updated_at >= ?
          AND last_error IS NOT NULL
          AND (last_error LIKE '%4016%' OR last_error LIKE '%欠费%' OR last_error LIKE '%认证%' OR last_error LIKE '%auth%')
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (since,),
    ).fetchone()
    return row

conn = sqlite3.connect(DB)
with LOG.open('a', encoding='utf-8') as log:
    log.write(f'\n=== search phase2 round2 start {MARK} ===\n')
    for keyword in KEYWORDS:
        for sort in SORTS:
            since = datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
            cmd = [
                sys.executable, '-m', 'src.jd.direct.search',
                '--q', keyword, '--sort', sort,
                '--max-pages', '20', '--workers', '4', '--delay', '0.15',
                '--timeout', '45', '--retries', '3', '--db', DB,
            ]
            print(f'RUN keyword={keyword} sort={sort!r}', flush=True)
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
            log.write(f'\n=== RUN keyword={keyword} sort={sort!r} started={since} ===\n')
            log.write(proc.stdout)
            log.write(proc.stderr)
            log.write(f'\nexit={proc.returncode}\n')
            log.flush()
            hit = check_4016_since(conn, since)
            print(f'DONE keyword={keyword} sort={sort!r} exit={proc.returncode}', flush=True)
            if hit:
                print(f'STOP 4016 keyword={keyword} sort={sort!r} updated_at={hit[2]} error={hit[1]}', flush=True)
                log.write(f'STOP 4016 keyword={keyword} sort={sort!r} updated_at={hit[2]} error={hit[1]}\n')
                raise SystemExit(2)
print(str(LOG))
