"""Service adapter for the signed Tmall SKU adjustment endpoint."""

from typing import Any

from src.tmall.direct.pcdetail_adjust import request_adjust


def run(input: dict[str, Any], cookie: str | None, proxy_url: str | None = None) -> dict[str, Any]:
    if proxy_url:
        raise ValueError("tmall.sku-adjust proxy transport is not implemented")
    if not cookie:
        raise ValueError("A Tmall credential profile is required")
    sku_id = str(input["sku_id"])
    status, payload, _ = request_adjust(cookie, sku_id)
    return {"http_status": status, "payload": payload}
