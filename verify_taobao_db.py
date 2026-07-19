import sqlite3
conn = sqlite3.connect('data/taobao_items.sqlite3')
try:
    print('STATUS_COUNTS', conn.execute('select status,count(*) from taobao_item_details group by status').fetchall())
    print('ERROR_COUNTS_TOP5', conn.execute('select last_error,count(*) from taobao_item_details group by last_error order by count(*) desc limit 5').fetchall())
    print('TOTAL', conn.execute('select count(*) from taobao_item_details').fetchone()[0])
    print('SUCCESS', conn.execute("select count(*) from taobao_item_details where status='success'").fetchone()[0])
finally:
    conn.close()
