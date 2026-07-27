"""API adapter for the Taobao shop gateway crawler."""

from typing import Any
from urllib.request import ProxyHandler, build_opener

from backend.app.core.config import get_settings
from src.taobao.direct.shop import CrawlerConfig, fetch_page


def run_taobao_shop(input: dict[str, Any], _: str | None, proxy_url: str | None = None) -> dict[str, Any]:
    """Fetch one Taobao shop listing page without creating SQLite files."""
    shop_id = str(input.get("shop_id") or "").strip()
    seller_id = str(input.get("seller_id") or "").strip()
    if not shop_id or not seller_id:
        raise ValueError("SHOP_ID_AND_SELLER_ID_REQUIRED")
    settings = get_settings()
    if not settings.fanb_api_key or not settings.fanb_api_secret:
        raise ValueError("CRAWLER_GATEWAY_CREDENTIALS_NOT_CONFIGURED")
    page = int(input.get("page") or 1)
    if page < 1:
        raise ValueError("PAGE_MUST_BE_POSITIVE")
    config = CrawlerConfig(
        key=settings.fanb_api_key,
        secret=settings.fanb_api_secret,
        shop_id=shop_id,
        seller_id=seller_id,
        max_items=1,
        start_page=page,
        sort=str(input.get("sort") or ""),
        cache=str(input.get("cache") or "no"),
        lang=str(input.get("lang") or "zh-CN"),
        timeout=float(input.get("timeout") or 30),
        retries=2,
        delay=0,
    )
    opener = build_opener(ProxyHandler({"http": proxy_url, "https": proxy_url})) if proxy_url else None
    response = fetch_page(config, page, opener=opener.open if opener else __import__("urllib.request").request.urlopen)
    return {"shop_id": shop_id, "seller_id": seller_id, "page": page, "payload": response}
