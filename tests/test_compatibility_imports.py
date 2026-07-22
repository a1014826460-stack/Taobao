def test_legacy_modules_reexport_relocated_functions():
    from src import item_crawler, jd_item_crawler
    from src.jd.direct import item as jd_item
    from src.taobao.direct import item as taobao_item
    from src.tmall.services import sku_adjust_service

    assert item_crawler.crawl_items is taobao_item.crawl_items
    assert jd_item_crawler.crawl_jd_items is jd_item.crawl_jd_items
    assert callable(sku_adjust_service.run)
