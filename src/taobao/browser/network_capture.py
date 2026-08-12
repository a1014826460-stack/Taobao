"""Utilities for capturing and safely persisting browser network responses."""
from __future__ import annotations
import json, re
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_SECRET_KEYS = re.compile(r"(?:cookie|set[-_]?cookie|authorization|x[-_]?token|token|sign|signature|auth)", re.I)
_MAX_BODY = 2 * 1024 * 1024


def _is_secret_key(key: str) -> bool:
    return bool(_SECRET_KEYS.fullmatch(str(key)) or _SECRET_KEYS.search(str(key)))


def redact_url(url: str) -> str:
    try:
        p = urlsplit(url)
        pairs = [(k, '[REDACTED]' if _is_secret_key(k) else v) for k,v in parse_qsl(p.query, keep_blank_values=True)]
        return urlunsplit((p.scheme, p.netloc, p.path, urlencode(pairs), p.fragment))
    except Exception:
        return url


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    out = {}
    for k,v in headers.items():
        out[str(k)] = '[REDACTED]' if _is_secret_key(str(k)) else str(v)
    return out


def _redact_obj(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ('[REDACTED]' if _is_secret_key(str(k)) else _redact_obj(v)) for k,v in value.items()}
    if isinstance(value, list): return [_redact_obj(v) for v in value]
    return value


def try_parse_json(body: str, content_type: str | None = None) -> Any | None:
    if not body or len(body) > _MAX_BODY: return None
    if content_type and 'json' not in content_type.lower() and not body.lstrip().startswith(('{','[')):
        return None
    try: return json.loads(body.lstrip('\ufeff'))
    except (TypeError, ValueError, json.JSONDecodeError): return None


def _walk_dicts(payload: Any):
    if isinstance(payload, dict):
        yield payload
        for v in payload.values(): yield from _walk_dicts(v)
    elif isinstance(payload, list):
        for v in payload: yield from _walk_dicts(v)


def classify_json(url: str, resource_type: str, payload: Any) -> str:
    """Classify by payload structure, not endpoint naming."""
    keys = {str(k).lower() for d in _walk_dicts(payload) for k in d.keys()}
    if any(k in keys for k in ('commentid','comments','ratecontent','reviewlist','评价')):
        return 'comments'
    # A seller-only response generally has seller/shop identifiers and no item payload.
    if ('sellerid' in keys or 'shopid' in keys or 'shopname' in keys) and not any(k in keys for k in ('itemid','item_id','itemidstr','auctionid')):
        return 'seller'
    if any(k in keys for k in ('itemid','item_id','itemidstr','auctionid','auction_id')):
        if any(k in keys for k in ('items','itemlist','results','result','goods','products','list')) or isinstance(payload, list):
            return 'search'
        return 'product_detail'
    if any(k in keys for k in ('items','itemlist','results','goods','products')):
        return 'search'
    return 'unknown_json'


def build_network_record(meta: dict, body: str | None) -> dict:
    rec = dict(meta or {})
    rec['url'] = redact_url(str(rec.get('url','')))
    if isinstance(rec.get('headers'), Mapping): rec['headers'] = redact_headers(rec['headers'])
    raw = body or ''
    if len(raw) > _MAX_BODY: raw = raw[:_MAX_BODY]
    payload = try_parse_json(raw, rec.get('content_type') or rec.get('mime_type'))
    if payload is not None:
        clean = _redact_obj(payload)
        rec['body'] = json.dumps(clean, ensure_ascii=False, separators=(',', ':'))
        rec['json_payload'] = clean
        rec['json_type'] = classify_json(rec['url'], str(rec.get('resource_type','')), clean)
    else:
        # Redact common secret query-like fragments in non-JSON bodies too.
        rec['body'] = re.sub(r'(?i)((?:token|sign|authorization|cookie)=)[^&\\s]+', r'\1[REDACTED]', raw)
        rec['json_payload'] = None
        rec['json_type'] = 'unknown_json'
    return rec
