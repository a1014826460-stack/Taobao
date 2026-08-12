import json
from taobao.browser.network_capture import redact_url, redact_headers, try_parse_json, classify_json, build_network_record

def test_redact_url_and_headers():
    u='https://x.test/api?token=SECRET&sign=abc&foo=1'; out=redact_url(u)
    assert 'SECRET' not in out and 'abc' not in out and 'foo=1' in out
    h=redact_headers({'Cookie':'sid=SECRET','Authorization':'Bearer TOKEN','X-Token':'abc','Accept':'json','Set-Cookie':'x=y'})
    assert all(v not in str(h) for v in ['SECRET','TOKEN','abc']); assert h['Accept']=='json'

def test_parse_json_content_and_malformed():
    assert try_parse_json('{"itemId":"1"}','application/json')['itemId']=='1'; assert try_parse_json('{"itemId":"1"}',None)['itemId']=='1'; assert try_parse_json('not-json','application/json') is None; assert try_parse_json('<html>','text/html') is None

def test_classify_fixtures():
    fixtures='tests/fixtures/taobao_browser'
    for name, expected in [('search.json','search'),('detail.json','product_detail'),('comments.json','comments'),('seller.json','seller')]:
        payload=json.load(open(f'{fixtures}/{name}', encoding='utf-8')); assert classify_json('https://x.test/api', 'xhr', payload)==expected
    assert classify_json('https://x.test/api','fetch', {'hello':'world'})=='unknown_json'

def test_build_network_record_redacts_body_and_metadata():
    rec=build_network_record({'url':'https://x.test?a=1&token=SECRET','method':'GET','status':200,'resource_type':'xhr','headers':{'Authorization':'Bearer SECRET'}}, '{"token":"SECRET","itemId":"1"}')
    assert 'SECRET' not in rec['url']; assert 'SECRET' not in rec['headers']['Authorization']; assert 'SECRET' not in rec['body']; assert rec['json_type']=='product_detail'; assert rec['json_payload']['itemId']=='1'
