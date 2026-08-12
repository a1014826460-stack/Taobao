import sqlite3, os
p='data/guonei_upload_state.sqlite3'
print(os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else 0)
if os.path.exists(p):
 con=sqlite3.connect(p); cur=con.cursor()
 names=[r[0] for r in cur.execute("select name from sqlite_master where type='table'")]
 for name in names:
  print('TABLE',name)
  print(cur.execute(f'pragma table_info({name})').fetchall())
  try: print('count',cur.execute(f'select count(*) from {name}').fetchone()[0])
  except Exception as e: print(e)
 con.close()
