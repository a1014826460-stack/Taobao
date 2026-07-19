from src.tests.taobao_batch import build_session, DEFAULT_HEADERS, DEFAULT_COOKIES
import re
s=build_session()
ids=['1045454678464','10095817869841','10124273278952','64165316038']
hosts=['https://detail.tmall.com/item.htm','https://item.taobao.com/item.htm']
for item_id in ids:
  print('\nID', item_id)
  for host in hosts:
    r=s.get(host, params={'id':item_id,'addressId':'22802236364'}, headers=DEFAULT_HEADERS, cookies=DEFAULT_COOKIES, timeout=30)
    h=r.text
    title=re.search(r'<title>(.*?)</title>', h, re.S)
    print(host, 'status', r.status_code, 'final', r.url[:120], 'len', len(h), 'ice', h.find('__ICE_APP_CONTEXT__'), 'loader', h.find('loaderData'), 'login', h.find('login'), 'title', title.group(1)[:80] if title else None, 'head', h[:80].replace('\n',' '))
