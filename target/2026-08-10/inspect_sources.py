import sqlite3
con=sqlite3.connect('data/taobao_item_get.sqlite3')
cur=con.cursor()
for r in cur.execute('select keyword, sort, count(distinct num_iid) from item_detail_sources group by keyword, sort order by keyword, sort limit 80'):
 print(r)
con.close()
