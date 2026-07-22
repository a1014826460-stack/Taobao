from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CrawlerName(StrEnum):
    TAOBAO_ITEM = "taobao.item"
    TAOBAO_SHOP = "taobao.shop"
    TMALL_SKU_ADJUST = "tmall.sku-adjust"
    JD_ITEM = "jd.item"
    JD_WARE_BUSINESS = "jd.ware-business"


class CrawlerExecution(BaseModel):
    crawler: CrawlerName
    input: dict[str, Any] = Field(default_factory=dict)
    credential_profile_id: str | None = None
    proxy_profile_id: str | None = None
