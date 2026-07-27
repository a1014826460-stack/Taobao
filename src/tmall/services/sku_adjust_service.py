"""Service adapter for the signed Tmall SKU adjustment endpoint."""

from typing import Any

from src.tmall.direct.pcdetail_adjust import request_adjust


def run(input: dict[str, Any], cookie: str | None, proxy_url: str | None = None) -> dict[str, Any]:
    if not cookie:
        raise ValueError("A Tmall credential profile is required")
    sku_id = str(input.get("sku_id") or "").strip()
    if not sku_id:
        raise ValueError("SKU_ID_REQUIRED")
    status, payload, _ = request_adjust(cookie, sku_id, proxy_url=proxy_url)
    return {"http_status": status, "payload": payload}
