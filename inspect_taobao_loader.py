from src.tests.taobao_test import fetch_item_page
import re
r = fetch_item_page(timeout=30)
html = r.text
print('status=', r.status_code, 'len=', len(html))
for pat in ['loaderData', '__ICE_APP_CONTEXT__', 'data-loader.js', 'window.__ICE_APP_CONTEXT__', 'serverData', 'ssrItemId']:
    print(pat, html.find(pat))
idx = html.find('loaderData')
print('\nloaderData context:')
print(html[max(0, idx-500):idx+800] if idx >= 0 else 'not found')
print('\ninline script containing loaderData:')
for m in re.finditer(r'<script[^>]*>(.*?)</script>', html, flags=re.S|re.I):
    body = m.group(1)
    if 'loaderData' in body:
        print('script_start=', m.start(), 'script_len=', len(body))
        print(m.group(0)[:1600])
        break
else:
    print('no inline script with loaderData')
print('\nexternal script tags around data-loader:')
for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\'][^>]*>', html, flags=re.I):
    src = m.group(1)
    if 'data-loader' in src or '@ali/tbpc-pc-detail' in src:
        print(src)
