import pytest

from backend.app.services.crawlers import REGISTRY


@pytest.mark.parametrize(
    "crawler",
    [
        "taobao.item",
        "taobao.shop",
        "tmall.sku-adjust",
        "jd.item",
        "jd.ware-business",
    ],
)
def test_every_public_crawler_has_a_configured_adapter(crawler):
    adapter = REGISTRY[crawler]

    assert callable(adapter)
    assert adapter.__module__ != "backend.app.services.crawlers"
