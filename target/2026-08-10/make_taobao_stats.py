import sqlite3, csv, os, re
from collections import defaultdict, Counter
SEARCH_DB='data/taobao_search.sqlite3'
DETAIL_DB='data/taobao_item_get.sqlite3'
OUT_DIR='target/taobao_19_keywords_detail_stats_20260730'
os.makedirs(OUT_DIR, exist_ok=True)
keywords=['高潮液','快感液','延时喷剂','飞机杯','电动飞机杯','男用自慰器','跳蛋','穿戴跳蛋','遥控跳蛋','情趣按摩棒','震动棒','AV棒','吸吮跳蛋','仿真阳具','肛塞','前列腺按摩器','倒模','名器','润滑液']
similar={
'高潮液':['女性高潮液','高潮润滑液','催情高潮液','女用快感液'],
'快感液':['女性快感液','女用快感液','快感润滑液','催情快感液'],
'延时喷剂':['男用延时喷剂','持久延时喷剂','延时液喷剂','房事延时喷剂'],
'飞机杯':['男用飞机杯','自慰杯'],
'电动飞机杯':['自动飞机杯','电动自慰杯','智能飞机杯','震动飞机杯'],
'男用自慰器':['男士自慰器','男性自慰器','男用情趣用品'],
'跳蛋':['震动跳蛋','无线跳蛋'],
'穿戴跳蛋':['可穿戴跳蛋','内裤跳蛋','穿戴震动跳蛋'],
'遥控跳蛋':['无线遥控跳蛋','手机遥控跳蛋','情趣遥控跳蛋'],
'情趣按摩棒':['女用按摩棒','情趣震动棒'],
'震动棒':['女用震动棒','情趣震动棒'],
'AV棒':['AV震动棒','AV按摩棒','女用AV棒','成人AV棒'],
'吸吮跳蛋':['吸吮震动棒','吮吸跳蛋'],
'仿真阳具':['仿真男根','假阳具','仿真按摩棒','硅胶阳具'],
'肛塞':['后庭肛塞','震动肛塞','情趣肛塞','硅胶肛塞'],
'前列腺按摩器':['男用前列腺按摩器','前列腺震动按摩器','后庭按摩器','男士按摩器'],
'倒模':['倒模名器','女优倒模','飞机杯倒模','真人倒模'],
'名器':['女优名器','倒模名器','男用名器','飞机杯名器'],
'润滑液':[]
}
con=sqlite3.connect(DETAIL_DB)
cur=con.cursor()
# status by keyword all sources
summary=[]
term_rows=[]
status_cols=['success','not_found','blocked_5000_pro','abandoned_503','retryable','error','no_state']
for kw in keywords:
    terms=[kw]+similar.get(kw,[])
    # keyword-level union: all item_detail_sources.keyword = original kw
    ids=[r[0] for r in cur.execute('select distinct num_iid from item_detail_sources where keyword=?',(kw,))]
    st=Counter()
    if ids:
        q=','.join('?'*len(ids))
        state=dict(cur.execute(f'select num_iid,status from item_detail_state where num_iid in ({q})', ids).fetchall())
        for iid in ids: st[state.get(iid,'no_state')]+=1
    success=st['success']
    total=len(ids)
    summary.append({
        'keyword':kw,'similar_terms':'|'.join(similar.get(kw,[])),'source_items':total,'success':success,
        'success_rate': f'{(success/total*100):.2f}%' if total else '0.00%',
        **{c:st[c] for c in status_cols if c!='success'},
        'latest_source_at': cur.execute('select max(created_at) from item_detail_sources where keyword=?',(kw,)).fetchone()[0] or '',
    })
    # term-level: original = non-similar sorts; each similar term via sort prefix similar:term:
    for term in terms:
        if term==kw:
            cond="keyword=? and sort not like 'similar:%'"; params=(kw,)
        else:
            cond="keyword=? and sort like ?"; params=(kw, f'similar:{term}:%')
        ids=[r[0] for r in cur.execute(f'select distinct num_iid from item_detail_sources where {cond}', params)]
        st=Counter()
        if ids:
            q=','.join('?'*len(ids))
            state=dict(cur.execute(f'select num_iid,status from item_detail_state where num_iid in ({q})', ids).fetchall())
            for iid in ids: st[state.get(iid,'no_state')]+=1
        term_rows.append({
            'keyword':kw,'term':term,'term_type':'原关键词' if term==kw else '相似词','source_items':len(ids),'success':st['success'],
            'success_rate': f'{(st["success"]/len(ids)*100):.2f}%' if ids else '0.00%',
            **{c:st[c] for c in status_cols if c!='success'},
            'latest_source_at': cur.execute(f'select max(created_at) from item_detail_sources where {cond}', params).fetchone()[0] or '',
        })
# write csvs
for fname, rows in [('summary_by_keyword.csv',summary),('detail_by_keyword_and_term.csv',term_rows)]:
    path=os.path.join(OUT_DIR,fname)
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
# markdown report
md=[]
md.append('# 淘宝19个关键词及相似词详情页抓取统计\n')
md.append('数据源：`data/taobao_item_get.sqlite3`，仅本地统计，未访问付费 API。\n')
md.append('\n## 按原关键词汇总（包含该关键词下所有相似词来源去重）\n')
md.append('|关键词|相似词|来源商品数|成功详情|成功率|not_found|blocked_5000|503放弃|retryable|error|未入状态|最新来源时间|')
md.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|')
for r in summary:
    md.append(f"|{r['keyword']}|{r['similar_terms']}|{r['source_items']}|{r['success']}|{r['success_rate']}|{r.get('not_found',0)}|{r.get('blocked_5000_pro',0)}|{r.get('abandoned_503',0)}|{r.get('retryable',0)}|{r.get('error',0)}|{r.get('no_state',0)}|{r['latest_source_at']}|")
md.append('\n## 按关键词/相似词拆分\n')
md.append('|原关键词|词|类型|来源商品数|成功详情|成功率|not_found|blocked_5000|503放弃|retryable|error|未入状态|')
md.append('|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
for r in term_rows:
    md.append(f"|{r['keyword']}|{r['term']}|{r['term_type']}|{r['source_items']}|{r['success']}|{r['success_rate']}|{r.get('not_found',0)}|{r.get('blocked_5000_pro',0)}|{r.get('abandoned_503',0)}|{r.get('retryable',0)}|{r.get('error',0)}|{r.get('no_state',0)}|")
with open(os.path.join(OUT_DIR,'report.md'),'w',encoding='utf-8') as f: f.write('\n'.join(md))
print('OUT_DIR', OUT_DIR)
print('TOTAL source_items', sum(r['source_items'] for r in summary), 'success', sum(r['success'] for r in summary))
for r in summary:
    print(r['keyword'], r['source_items'], r['success'], r['success_rate'])
con.close()
