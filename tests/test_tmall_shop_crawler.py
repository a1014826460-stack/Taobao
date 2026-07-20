import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import tmall_shop_crawler


class TmallRequestAndParserTests(unittest.TestCase):
    def test_parse_cookie_header_ignores_malformed_segments(self):
        self.assertEqual(
            tmall_shop_crawler.parse_cookie_header(
                "a=1; invalid; b=two=parts; =missing"
            ),
            {"a": "1", "b": "two=parts"},
        )

    def test_build_page_request_uses_shop_search_and_page_number(self):
        request_url, params, headers = tmall_shop_crawler.build_page_request(
            "https://iqoo.tmall.com/search.htm?orderType=defaultSort&viewType=grid",
            2,
        )
        self.assertEqual(request_url, "https://iqoo.tmall.com/i/asynSearch.htm")
        self.assertEqual(params["path"], "/search.htm")
        self.assertEqual(params["orderType"], "defaultSort")
        self.assertEqual(params["viewType"], "grid")
        self.assertEqual(params["pageNo"], "2")
        self.assertEqual(
            headers["Referer"],
            "https://iqoo.tmall.com/search.htm?orderType=defaultSort&viewType=grid",
        )

    def test_build_page_request_rejects_domains_that_only_end_with_tmall_dot_com(self):
        with self.assertRaisesRegex(ValueError, "Tmall"):
            tmall_shop_crawler.build_page_request(
                "https://not-tmall.com/search.htm", 1
            )

    def test_decode_jsonp_and_extract_product_fields(self):
        payload = {
            "itemList": [
                {"item_id": "1001", "title": "Test item", "price": "9.90"}
            ]
        }
        parsed = tmall_shop_crawler.decode_payload("jsonp91(" + json.dumps(payload) + ");")
        items = tmall_shop_crawler.extract_products(parsed, 1)
        self.assertEqual(items[0]["item_id"], "1001")
        self.assertEqual(items[0]["title"], "Test item")
        self.assertEqual(items[0]["page_number"], 1)

    def test_decode_jsonp_unwraps_an_html_string_payload(self):
        self.assertEqual(
            tmall_shop_crawler.decode_payload('jsonp91("<dl data-id=\\\"1001\\\"></dl>")'),
            "<dl data-id=\"1001\"></dl>",
        )

    def test_decode_jsonp_accepts_control_characters_in_html_strings(self):
        self.assertEqual(
            tmall_shop_crawler.decode_payload('jsonp91("<dl>first\nsecond</dl>")'),
            "<dl>first\nsecond</dl>",
        )

    def test_extract_products_from_tmall_html_item_rows(self):
        html = '''
        <dl class="item" data-id="1001">
          <a class="J_TGoldData" href="//detail.tmall.com/item.htm?id=1001"></a>
          <img data-ks-lazyload="//img.example/1001.jpg" alt="Test item" />
          <div class="detail"><a>Test item</a></div>
          <span class="c-price">9.90</span>
          <span class="sale-num">100 people paid</span>
        </dl>
        '''
        items = tmall_shop_crawler.extract_products(html, 1)
        self.assertEqual(items[0]["item_id"], "1001")
        self.assertEqual(items[0]["title"], "Test item")
        self.assertEqual(items[0]["price"], "9.90")
        self.assertEqual(items[0]["item_url"], "https://detail.tmall.com/item.htm?id=1001")

    def test_store_page_upserts_items_and_raw_page(self):
        with tempfile.TemporaryDirectory() as directory:
            store = tmall_shop_crawler.TmallShopStore(Path(directory) / "shop.sqlite3")
            store.save_page(
                shop_url="https://iqoo.tmall.com/search.htm",
                page_number=1,
                raw_payload={"itemList": [{"item_id": "1001"}]},
                items=[{"item_id": "1001", "title": "Old title", "page_number": 1}],
            )
            store.save_page(
                shop_url="https://iqoo.tmall.com/search.htm",
                page_number=1,
                raw_payload={"itemList": [{"item_id": "1001"}]},
                items=[{"item_id": "1001", "title": "New title", "page_number": 1}],
            )
            self.assertEqual(store.count_pages(), 1)
            self.assertEqual(store.count_items(), 1)
            self.assertEqual(
                store.get_item("https://iqoo.tmall.com/search.htm", "1001")["title"],
                "New title",
            )
            store.close()

    def test_crawl_pages_saves_a_non_overlapping_two_page_range(self):
        with tempfile.TemporaryDirectory() as directory:
            store = tmall_shop_crawler.TmallShopStore(Path(directory) / "shop.sqlite3")
            try:
                def fake_fetcher(page_number):
                    return {
                        "itemList": [
                            {"item_id": str(page_number), "title": f"page {page_number}"}
                        ]
                    }

                result = tmall_shop_crawler.crawl_pages(
                    shop_url="https://iqoo.tmall.com/search.htm",
                    start_page=1,
                    pages=2,
                    fetcher=fake_fetcher,
                    store=store,
                )
                self.assertEqual(result.page_item_counts, {1: 1, 2: 1})
                self.assertEqual(result.total_items, 2)
                self.assertEqual(store.count_pages(), 2)
                self.assertEqual(store.count_items(), 2)
            finally:
                store.close()

    def test_crawl_until_end_stops_when_a_page_is_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            store = tmall_shop_crawler.TmallShopStore(Path(directory) / "shop.sqlite3")
            try:
                def fake_fetcher(page_number):
                    return {"itemList": [{"item_id": "1"}]} if page_number == 1 else {"itemList": []}

                result = tmall_shop_crawler.crawl_until_end(
                    "https://iqoo.tmall.com/search.htm", 1, fake_fetcher, store
                )
                self.assertEqual(result.page_item_counts, {1: 1})
                self.assertEqual(result.total_items, 1)
                self.assertEqual(result.skipped_duplicates, 0)
                self.assertEqual(result.stop_reason, "empty_page")
            finally:
                store.close()

    def test_crawl_until_end_skips_a_product_id_repeated_across_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            store = tmall_shop_crawler.TmallShopStore(Path(directory) / "shop.sqlite3")
            try:
                def fake_fetcher(page_number):
                    if page_number == 1:
                        return {"itemList": [{"item_id": "repeated"}, {"item_id": "one"}]}
                    if page_number == 2:
                        return {"itemList": [{"item_id": "repeated"}, {"item_id": "two"}]}
                    return {"itemList": []}

                result = tmall_shop_crawler.crawl_until_end(
                    "https://iqoo.tmall.com/search.htm", 1, fake_fetcher, store
                )
                self.assertEqual(result.page_item_counts, {1: 2, 2: 1})
                self.assertEqual(result.total_items, 3)
                self.assertEqual(result.skipped_duplicates, 1)
                self.assertEqual(store.count_items(), 3)
            finally:
                store.close()

    def test_has_next_page_recognizes_disabled_next_link(self):
        self.assertFalse(
            tmall_shop_crawler.has_next_page(
                '<div class="pagination"><a class="disable">下一页</a></div>'
            )
        )
        self.assertTrue(
            tmall_shop_crawler.has_next_page(
                '<div class="pagination"><a class="next" href="?pageNo=2">下一页</a></div>'
            )
        )

    def test_has_next_page_reads_legacy_page_counter(self):
        self.assertFalse(
            tmall_shop_crawler.has_next_page(
                '<p><b class="ui-page-s-len">1/1</b><b title="下一页" class="ui-page-s-next">&gt;</b></p>'
            )
        )
        self.assertTrue(
            tmall_shop_crawler.has_next_page(
                '<p><b class="ui-page-s-len">1/3</b><b title="下一页" class="ui-page-s-next">&gt;</b></p>'
            )
        )

    def test_crawl_pages_deduplicates_repeated_rendering_of_one_page_item(self):
        with tempfile.TemporaryDirectory() as directory:
            store = tmall_shop_crawler.TmallShopStore(Path(directory) / "shop.sqlite3")
            try:
                result = tmall_shop_crawler.crawl_pages(
                    "https://iqoo.tmall.com/search.htm",
                    1,
                    1,
                    lambda page_number: {
                        "itemList": [
                            {"item_id": "duplicated", "title": "first"},
                            {"item_id": "duplicated", "title": "second"},
                        ]
                    },
                    store,
                )
                self.assertEqual(result.page_item_counts, {1: 1})
                self.assertEqual(result.total_items, 1)
                self.assertEqual(store.count_items(), 1)
            finally:
                store.close()

    def test_config_from_args_requires_cookie_and_parses_it_when_present(self):
        args = tmall_shop_crawler.parse_args(
            [
                "--shop-url",
                "https://iqoo.tmall.com/search.htm",
                "--start-page",
                "1",
            ]
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "TAOBAO_COOKIE"):
                tmall_shop_crawler.config_from_args(args)
        with mock.patch.dict(os.environ, {"TAOBAO_COOKIE": "a=1; b=2"}, clear=True):
            config = tmall_shop_crawler.config_from_args(args)
        self.assertEqual(config.cookies, {"a": "1", "b": "2"})
        self.assertIsNone(config.pages)

    def test_fetch_page_uses_proxy_free_session_cookies_timeout_and_jsonp(self):
        class FakeResponse:
            text = 'jsonp91({"itemList":[{"item_id":"1"}]});'
            url = "https://iqoo.tmall.com/i/asynSearch.htm"

            def raise_for_status(self):
                return None

        class FakeSession:
            def __init__(self):
                self.trust_env = True
                self.request = None

            def get(self, url, **kwargs):
                self.request = (url, kwargs)
                return FakeResponse()

        session = FakeSession()
        config = tmall_shop_crawler.CrawlerConfig(
            shop_url="https://iqoo.tmall.com/search.htm",
            start_page=1,
            pages=2,
            db_path=Path("data/test.sqlite3"),
            timeout=12,
            cookies={"a": "1"},
        )
        payload = tmall_shop_crawler.fetch_page(config, 1, session)
        self.assertFalse(session.trust_env)
        self.assertEqual(session.request[1]["cookies"], {"a": "1"})
        self.assertEqual(session.request[1]["timeout"], 12)
        self.assertEqual(payload["itemList"][0]["item_id"], "1")

    def test_fetch_page_rejects_a_redirected_error_page(self):
        class FakeResponse:
            text = "<html>not found</html>"
            url = "https://err.tmall.com/error"

            def raise_for_status(self):
                return None

        class FakeSession:
            trust_env = True

            def get(self, url, **kwargs):
                return FakeResponse()

        config = tmall_shop_crawler.CrawlerConfig(
            shop_url="https://iqoo.tmall.com/search.htm",
            start_page=1,
            pages=1,
            db_path=Path("data/test.sqlite3"),
            timeout=12,
            cookies={"a": "1"},
        )
        with self.assertRaisesRegex(ValueError, "neither JSON nor JSONP"):
            tmall_shop_crawler.fetch_page(config, 1, FakeSession())

    def test_main_returns_one_when_cookie_is_missing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                tmall_shop_crawler.main(
                    [
                        "--shop-url",
                        "https://iqoo.tmall.com/search.htm",
                        "--start-page",
                        "1",
                        "--pages",
                        "2",
                    ]
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
