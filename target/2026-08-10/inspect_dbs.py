import sqlite3, os
for p in ['data/taobao_search.sqlite3','data/taobao_item_get.sqlite3']:
    print('\nDB',p, os.path.getsize(p))
    con=sqlite3.connect(p)
    cur=con.cursor()
    cur.execute("select name,type from sqlite_master where type in ('table','view') order by name")
    for name,t in cur.fetchall():
        print(' ',t,name)
        cur.execute(f'pragma table_info("{name}")')
        cols=cur.fetchall()
        print('   cols:', ', '.join([c[1]+':' + c[2] for c in cols]))
        try:
            cur.execute(f'select count(*) from "{name}"')
            print('   count:', cur.fetchone()[0])
        except Exception as e: print('   count err',e)
    con.close()
