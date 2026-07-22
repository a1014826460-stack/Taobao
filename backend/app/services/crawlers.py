from typing import Any, Callable

from src.tmall.services.sku_adjust_service import run as tmall_sku_adjust


def unavailable(name: str) -> Callable[[dict[str, Any], str | None, str | None], dict[str, Any]]:
    def run(_: dict[str, Any], __: str | None, ___: str | None) -> dict[str, Any]:
        raise ValueError(f"{name} service adapter has not been configured")
    return run


REGISTRY: dict[str, Callable[[dict[str, Any], str | None, str | None], dict[str, Any]]] = {
    "taobao.item": unavailable("taobao.item"),
    "taobao.shop": unavailable("taobao.shop"),
    "tmall.sku-adjust": tmall_sku_adjust,
    "jd.item": unavailable("jd.item"),
    "jd.ware-business": unavailable("jd.ware-business"),
}
