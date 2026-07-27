"""API adapter for the Taobao item gateway crawler."""

from typing import Any
from urllib.request import ProxyHandler, build_opener

from backend.app.core.config import get_settings
from src.taobao.direct.item import ItemCrawlerConfig, fetch_item_detail


def _gateway_credentials() -> tuple[str, str]:
    settings = get_settings()
    if not settings.fanb_api_key or not settings.fanb_api_secret:
        raise ValueError("CRAWLER_GATEWAY_CREDENTIALS_NOT_CONFIGURED")
    return settings.fanb_api_key, settings.fanb_api_secret


def _opener(proxy_url: str | None):
    return build_opener(ProxyHandler({"http": proxy_url, "https": proxy_url})) if proxy_url else None


def run_taobao_item(input: dict[str, Any], _: str | None, proxy_url: str | None = None) -> dict[str, Any]:
    """Fetch one Taobao item without writing crawl data to disk."""
    item_id = str(input.get("item_id") or input.get("num_iid") or "").strip()
    if not item_id:
        raise ValueError("ITEM_ID_REQUIRED")
    key, secret = _gateway_credentials()
    config = ItemCrawlerConfig(
        key=key,
        secret=secret,
        num_iids=[item_id],
        item_api=str(input.get("item_api") or "item_get_pro"),
        is_promotion=input.get("is_promotion"),
        timeout=float(input.get("timeout") or 30),
        retries=2,
        delay=0,
    )
    opener = _opener(proxy_url)
    response = fetch_item_detail(config, item_id, opener=opener.open if opener else __import__("urllib.request").request.urlopen)
    return {"item_id": item_id, "payload": response}
