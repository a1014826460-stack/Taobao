from src.common.models.crawler import CrawlerExecution, CrawlerName


def test_execution_keeps_profile_ids_separate_from_input():
    execution = CrawlerExecution(
        crawler=CrawlerName.TMALL_SKU_ADJUST,
        input={"item_id": "1007839388129", "sku_id": "6277426546603"},
        credential_profile_id="credential-id",
        proxy_profile_id="proxy-id",
    )

    assert execution.input["sku_id"] == "6277426546603"
    assert execution.credential_profile_id == "credential-id"
    assert execution.proxy_profile_id == "proxy-id"
