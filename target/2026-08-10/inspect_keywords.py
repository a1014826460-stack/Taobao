import sqlite3, json, os
con=sqlite3.connect('data/taobao_item_get.sqlite3')
cur=con.cursor()
print('distinct keywords in detail_sources:', cur.execute('select count(distinct keyword) from item_detail_sources').fetchone()[0])
rows=cur.execute('select keyword, count(distinct num_iid) n, min(created_at), max(created_at) from item_detail_sources group by keyword order by n desc, keyword').fetchall()
for r in rows[:300]: print('\t'.join(map(str,r)))
print('statuses')
for r in cur.execute('select status,count(*) from item_detail_state group by status'): print(r)
print('errors')
for r in cur.execute('select status,last_error,count(*) from item_detail_state group by status,last_error order by count(*) desc limit 20'): print(r)
con.close()

con=sqlite3.connect('data/taobao_search.sqlite3')
cur=con.cursor()
print('\nsearch fingerprints', cur.execute('select count(distinct query_fingerprint) from search_items').fetchone()[0])
for r in cur.execute('select query_fingerprint, count(distinct num_iid) n, min(created_at), max(updated_at) from search_items group by query_fingerprint order by n desc limit 200'):
    print('\t'.join(map(str,r)))
con.close()
