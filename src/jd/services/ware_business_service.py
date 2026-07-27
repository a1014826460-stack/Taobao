"""Adapter for JD's pc_detailpage_wareBusiness request.

The endpoint's browser signature is short-lived.  This adapter deliberately
requires a freshly captured signed URL instead of storing or attempting to
replay browser fingerprints on behalf of another user.
"""

import json
from typing import Any
from urllib.request import ProxyHandler, Request, build_opener, urlopen


def run_jd_ware_business(input: dict[str, Any], cookie: str | None, proxy_url: str | None = None) -> dict[str, Any]:
    signed_url = str(input.get("signed_url") or "").strip()
    sku_id = str(input.get("sku_id") or input.get("item_id") or "").strip()
    if not sku_id:
        raise ValueError("SKU_ID_REQUIRED")
    if not signed_url.startswith("https://api.m.jd.com/"):
        raise ValueError("FRESH_JD_SIGNED_URL_REQUIRED")
    request = Request(
        signed_url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "Cookie": cookie or "",
            "Referer": f"https://item.jd.com/{sku_id}.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        },
    )
    opener = build_opener(ProxyHandler({"http": proxy_url, "https": proxy_url})) if proxy_url else None
    with (opener.open(request, timeout=30) if opener else urlopen(request, timeout=30)) as response:
        body = response.read().decode("utf-8", "replace")
        status = response.status
    try:
        payload: Any = json.loads(body)
    except json.JSONDecodeError:
        raise ValueError("JD_WARE_BUSINESS_INVALID_RESPONSE") from None
    return {"sku_id": sku_id, "http_status": status, "payload": payload}
