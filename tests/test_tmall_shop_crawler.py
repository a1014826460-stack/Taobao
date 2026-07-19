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

    def test_crawl_pages_rejects_an_empty_requested_page(self):
        with tempfile.TemporaryDirectory() as directory:
            store = tmall_shop_crawler.TmallShopStore(Path(directory) / "shop.sqlite3")
            try:
                def fake_fetcher(page_number):
                    return {"itemList": [{"item_id": "1"}]} if page_number == 1 else {"itemList": []}

                with self.assertRaisesRegex(
                    tmall_shop_crawler.CrawlValidationError, "page 2 is empty"
                ):
                    tmall_shop_crawler.crawl_pages(
                        "https://iqoo.tmall.com/search.htm", 1, 2, fake_fetcher, store
                    )
            finally:
                store.close()

    def test_crawl_pages_rejects_a_product_id_repeated_across_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            store = tmall_shop_crawler.TmallShopStore(Path(directory) / "shop.sqlite3")
            try:
                def fake_fetcher(page_number):
                    return {"itemList": [{"item_id": "repeated"}]}

                with self.assertRaisesRegex(
                    tmall_shop_crawler.CrawlValidationError, "repeated"
                ):
                    tmall_shop_crawler.crawl_pages(
                        "https://iqoo.tmall.com/search.htm", 1, 2, fake_fetcher, store
                    )
            finally:
                store.close()

    def test_config_from_args_requires_cookie_and_parses_it_when_present(self):
        args = tmall_shop_crawler.parse_args(
            [
                "--shop-url",
                "https://iqoo.tmall.com/search.htm",
                "--start-page",
                "1",
                "--pages",
                "2",
            ]
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "TAOBAO_COOKIE"):
                tmall_shop_crawler.config_from_args(args)
        with mock.patch.dict(os.environ, {"TAOBAO_COOKIE": "a=1; b=2"}, clear=True):
            config = tmall_shop_crawler.config_from_args(args)
        self.assertEqual(config.cookies, {"a": "1", "b": "2"})
        self.assertEqual(config.pages, 2)

    def test_fetch_page_uses_proxy_free_session_cookies_timeout_and_jsonp(self):
        class FakeResponse:
            text = 'tmallShopCallback({"itemList":[{"item_id":"1"}]});'

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
