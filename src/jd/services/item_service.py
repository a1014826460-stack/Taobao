"""API adapter for the JD item gateway crawler."""

from typing import Any
from urllib.request import ProxyHandler, build_opener

from backend.app.core.config import get_settings
from src.jd.direct.item import JDItemCrawlerConfig, fetch_jd_item_detail


def run_jd_item(input: dict[str, Any], _: str | None, proxy_url: str | None = None) -> dict[str, Any]:
    """Fetch one JD item without creating SQLite files."""
    item_id = str(input.get("item_id") or input.get("sku_id") or input.get("num_iid") or "").strip()
    if not item_id:
        raise ValueError("ITEM_ID_REQUIRED")
    settings = get_settings()
    if not settings.fanb_api_key or not settings.fanb_api_secret:
        raise ValueError("CRAWLER_GATEWAY_CREDENTIALS_NOT_CONFIGURED")
    config = JDItemCrawlerConfig(
        key=settings.fanb_api_key,
        secret=settings.fanb_api_secret,
        num_iids=[item_id],
        cache=str(input.get("cache") or "no"),
        lang=str(input.get("lang") or "zh-CN"),
        timeout=float(input.get("timeout") or 30),
        retries=2,
        delay=0,
    )
    opener = build_opener(ProxyHandler({"http": proxy_url, "https": proxy_url})) if proxy_url else None
    response = fetch_jd_item_detail(config, item_id, opener=opener.open if opener else __import__("urllib.request").request.urlopen)
    return {"item_id": item_id, "payload": response}
