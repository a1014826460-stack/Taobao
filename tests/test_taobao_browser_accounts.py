import json
from pathlib import Path
import pytest

from src.taobao.browser.accounts import (
    AccountRecord, CookieRecord, discover_accounts, parse_cookie_text, redact_cookie_value,
)

def test_semicolon_cookie_input():
    got = parse_cookie_text('sid=abc; theme=dark', 'taobao')
    assert [c.name for c in got] == ['sid', 'theme']
    assert got[0].value == 'abc' and got[0].domain == '.taobao.com'

def test_netscape_cookie_input():
    text = '# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tTRUE\t1730000000\tsid\tabc\n#HttpOnly_.taobao.com\tTRUE\t/\tFALSE\t0\tsec\tx'
    got = parse_cookie_text(text, 'cookies.txt')
    assert got[0].domain == '.example.com' and got[0].secure is True
    assert got[0].expires == 1730000000 and got[1].http_only is True

def test_json_array_and_wrapper_inputs():
    payload = json.dumps([{'name':'sid','value':'abc','domain':'.taobao.com','path':'/','httpOnly':True,'sameSite':'Lax'}])
    assert parse_cookie_text(payload, 'x.json')[0].http_only is True
    wrapped = json.dumps({'cookies':[{'name':'a','value':'b','secure':True}]})
    got = parse_cookie_text(wrapped, 'tmall.json')
    assert got[0].domain == '.tmall.com' and got[0].secure is True

def test_malformed_entries_rejected():
    with pytest.raises(ValueError): parse_cookie_text('missing_equals', 'x')
    with pytest.raises(ValueError): parse_cookie_text('[{"value":"x"}]', 'x')
    with pytest.raises(ValueError): parse_cookie_text('a=b\ttoo', 'x')

def test_discover_accounts_stable_stems(tmp_path: Path):
    (tmp_path/'zeta.txt').write_text('a=b', encoding='utf-8')
    (tmp_path/'alpha.json').write_text('[]', encoding='utf-8')
    got = discover_accounts(tmp_path)
    assert [a.account_id for a in got] == ['alpha','zeta']
    assert all(isinstance(a, AccountRecord) and a.status == 'active' for a in got)
    single = discover_accounts(tmp_path, tmp_path/'zeta.txt')
    assert [a.account_id for a in single] == ['zeta']

def test_redaction_never_exposes_value():
    value = 'secret-token-123'
    out = redact_cookie_value(value)
    assert value not in out and out != value
    assert redact_cookie_value(value) == out
