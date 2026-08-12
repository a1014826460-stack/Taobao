import sqlite3
con=sqlite3.connect('data/taobao_item_get.sqlite3')
cur=con.cursor()
print(cur.execute("select count(*) from item_details where trim(coalesce(raw_json,''))<>''").fetchone()[0])
print(cur.execute("select max(updated_at) from item_details").fetchone()[0])
print(cur.execute("select count(*) from item_details d join item_detail_state st on st.num_iid=d.num_iid where st.status='success' and d.updated_at>='2026-07-30T13:04:42+00:00'").fetchone()[0])
con.close()
