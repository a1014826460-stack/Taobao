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
import json
from taobao.browser.network_capture import build_network_record

def test_non_json_body_secret_redaction_all_keys():
    body='token=TOPSECRET&sign=SIG&signature=SIG2&x-token=XT&authorization=Bearer AUTH&cookie=CK&set-cookie=SC&ok=yes'
    rec=build_network_record({'url':'https://x.test','resource_type':'xhr'}, body)
    for secret in ('TOPSECRET','SIG','SIG2','XT','AUTH','CK','SC'):
        assert secret not in rec['body']
    assert 'ok=yes' in rec['body']

def test_meta_recursive_redaction():
    rec=build_network_record({'url':'https://x.test','token':'TOP','nested':{'sign':'S','safe':'ok'},'headers':{'X-Token':'XT'}}, None)
    dumped=json.dumps(rec)
    for secret in ('TOP','S','XT'): assert secret not in dumped
    assert rec['nested']['safe']=='ok'

def test_oversized_body_redacted_before_truncation():
    secret='ULTRA_SECRET_VALUE'
    body='x=' + ('a'* (2*1024*1024)) + '&token=' + secret
    rec=build_network_record({'url':'https://x.test'}, body)
    assert secret not in rec['body']
    assert len(rec['body']) <= 2*1024*1024
from taobao.browser.network_capture import build_network_record

def test_non_json_multitoken_and_quoted_secret_redaction():
    body='token=ONE TWO THREE&ok=1\nsign="A B C";next=yes'
    rec=build_network_record({'url':'https://x.test'}, body)
    for secret in ('ONE','TWO','THREE','A B C'): assert secret not in rec['body']
    assert 'ok=1' in rec['body'] and 'next=yes' in rec['body']

