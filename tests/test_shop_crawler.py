import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from urllib.parse import parse_qs, urlparse

from src.shop_crawler import (
    CrawlerConfig,
    SQLiteStore,
    build_arg_parser,
    config_from_args,
    config_from_item_args,
    crawl_shop,
    fetch_page,
    load_env,
    parse_cli_args,
)
from src.item_crawler import (
    ItemCrawlerConfig,
    SQLiteItemStore,
    crawl_items,
    fetch_item_detail,
    parse_num_iids,
)


class EnvTests(unittest.TestCase):
    def test_load_env_reads_key_value_pairs_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "password.env"
            env_path.write_text(
                "\n# comment\nkey = abc123\nsecret= shh \nEMPTY=\n",
                encoding="utf-8",
            )

            values = load_env(env_path)

        self.assertEqual(values["key"], "abc123")
        self.assertEqual(values["secret"], "shh")
        self.assertEqual(values["EMPTY"], "")
        self.assertNotIn("# comment", values)


class SQLiteStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "items.sqlite3")
        self.store = SQLiteStore(self.db_path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_save_page_upserts_items_and_tracks_next_page_by_shop_id(self):
        response = {
            "items": {
                "shop_id": "517932711",
                "page": "1",
                "page_count": 40,
                "total_results": 999,
                "real_total_results": 999,
                "item": [
                    {
                        "num_iid": 1060297494731,
                        "pic_url": "https://example.test/1.jpg",
                        "title": "first item",
                        "promotion_price": "51.33",
                        "price": "51.33",
                        "seller_id": "2200684271326",
                        "shop_id": "517932711",
                        "shop_name": "demo",
                        "detail_url": "https://item.taobao.com/item.htm?id=1060297494731",
                    }
                ],
                "page_size": 20,
            },
            "error_code": "0000",
        }

        saved = self.store.save_page(
            shop_id="517932711",
            seller_id="2200684271326",
            page=1,
            response=response,
            next_page=2,
            status="running",
        )
        repeated = self.store.save_page(
            shop_id="517932711",
            seller_id="changed-seller",
            page=1,
            response=response,
            next_page=2,
            status="running",
        )
        state = self.store.get_state("517932711")

        self.assertEqual(saved.inserted_items, 1)
        self.assertEqual(repeated.inserted_items, 0)
        self.assertEqual(state["shop_id"], "517932711")
        self.assertEqual(state["seller_id"], "changed-seller")
        self.assertEqual(state["next_page"], 2)
        self.assertEqual(state["fetched_items"], 1)
        self.assertIsNone(self.store.get_state("other-shop"))


class ItemInputTests(unittest.TestCase):
    def test_parse_num_iids_accepts_lists_commas_whitespace_and_deduplicates(self):
        values = parse_num_iids(
            ["520813250866, 599262347474", "520813250866\n1060297494731"]
        )

        self.assertEqual(values, ["520813250866", "599262347474", "1060297494731"])


class SQLiteItemStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "items.sqlite3")
        self.store = SQLiteItemStore(self.db_path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_save_item_detail_upserts_detail_and_tracks_success_state_by_num_iid(self):
        response = {
            "item": {
                "num_iid": "599262347474",
                "title": "sample item",
                "price": "67.00",
                "orginal_price": "67.00",
                "nick": "demo shop",
                "detail_url": "https://item.taobao.com/item.htm?id=599262347474",
                "pic_url": "//img.alicdn.com/example.jpg",
                "brand": "demo brand",
                "cid": "50016845",
                "seller_id": "3013891076",
                "shop_id": "486527013",
                "sales": 2,
            },
            "error_code": "0000",
        }

        self.store.mark_pending("599262347474")
        self.store.save_item_detail("599262347474", response)
        self.store.save_item_detail("599262347474", response)

        state = self.store.get_item_state("599262347474")
        detail = self.store.get_item_detail("599262347474")

        self.assertEqual(state["status"], "success")
        self.assertEqual(detail["num_iid"], "599262347474")
        self.assertEqual(detail["title"], "sample item")
        self.assertEqual(detail["shop_id"], "486527013")
        self.assertEqual(self.store.count_successful(), 1)

    def test_save_item_get_response_shape_to_database(self):
        response = {
            "item": {
                "num_iid": "652874751412",
                "title": "item_get sample",
                "price": "480.00",
                "orginal_price": "480.00",
                "nick": "sample shop",
                "detail_url": "https://item.taobao.com/item.htm?id=652874751412",
                "pic_url": "//img.alicdn.com/example.jpg",
                "brand": "#0 工厂",
                "cid": "50020632",
                "seller_id": "2568161054",
                "shop_id": "567158267",
                "sales": 0,
                "skus": {
                    "sku": [
                        {
                            "price": 480,
                            "orginal_price": 480,
                            "sku_id": "4881047531343",
                        }
                    ]
                },
            },
            "error_code": "0000",
            "api_info": "today:8 max:10000",
            "call_args": {
                "num_iid": "652874751412",
                "is_promotion": "1",
                "API_type": "taobao",
            },
            "api_type": "taobao",
        }

        self.store.save_item_detail("652874751412", response)

        detail = self.store.get_item_detail("652874751412")
        raw = json.loads(detail["raw_json"])
        self.assertEqual(detail["num_iid"], "652874751412")
        self.assertEqual(detail["title"], "item_get sample")
        self.assertEqual(detail["price"], "480.00")
        self.assertEqual(detail["shop_id"], "567158267")
        self.assertEqual(detail["sales"], "0")
        self.assertEqual(raw["call_args"]["is_promotion"], "1")


class CrawlItemsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "items.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def item_response(self, num_iid):
        return {
            "item": {
                "num_iid": str(num_iid),
                "title": f"item {num_iid}",
                "price": "9.90",
                "orginal_price": "19.90",
                "seller_id": "3013891076",
                "shop_id": "486527013",
            },
            "error_code": "0000",
        }

    def config(self, num_iids, reset_items=False):
        return ItemCrawlerConfig(
            key="demo-key",
            secret="demo-secret",
            num_iids=num_iids,
            db_path=self.db_path,
            reset_items=reset_items,
            delay=0,
        )

    def test_crawl_items_saves_each_detail(self):
        requested = []

        def fetcher(config, num_iid):
            requested.append(num_iid)
            return self.item_response(num_iid)

        result = crawl_items(self.config(["1", "2"]), fetcher=fetcher)

        store = SQLiteItemStore(self.db_path)
        try:
            self.assertEqual(requested, ["1", "2"])
            self.assertEqual(result.fetched, 2)
            self.assertEqual(result.skipped, 0)
            self.assertEqual(store.get_item_detail("1")["title"], "item 1")
            self.assertEqual(store.get_item_state("2")["status"], "success")
        finally:
            store.close()

    def test_crawl_items_skips_successful_ids_on_resume(self):
        first_requested = []

        def first_fetcher(config, num_iid):
            first_requested.append(num_iid)
            return self.item_response(num_iid)

        crawl_items(self.config(["1", "2"]), fetcher=first_fetcher)

        second_requested = []

        def second_fetcher(config, num_iid):
            second_requested.append(num_iid)
            return self.item_response(num_iid)

        result = crawl_items(self.config(["1", "2", "3"]), fetcher=second_fetcher)

        self.assertEqual(first_requested, ["1", "2"])
        self.assertEqual(second_requested, ["3"])
        self.assertEqual(result.fetched, 1)
        self.assertEqual(result.skipped, 2)

    def test_crawl_items_reset_items_refetches_successful_ids(self):
        def fetcher(config, num_iid):
            return self.item_response(num_iid)

        crawl_items(self.config(["1"]), fetcher=fetcher)

        requested = []

        def refetcher(config, num_iid):
            requested.append(num_iid)
            return self.item_response(num_iid)

        result = crawl_items(self.config(["1"], reset_items=True), fetcher=refetcher)

        self.assertEqual(requested, ["1"])
        self.assertEqual(result.fetched, 1)
        self.assertEqual(result.skipped, 0)

    def test_crawl_items_records_error_and_continues(self):
        def fetcher(config, num_iid):
            if num_iid == "bad":
                raise RuntimeError("boom")
            return self.item_response(num_iid)

        result = crawl_items(self.config(["bad", "good"]), fetcher=fetcher)

        store = SQLiteItemStore(self.db_path)
        try:
            self.assertEqual(result.failed, 1)
            self.assertEqual(result.fetched, 1)
            self.assertEqual(store.get_item_state("bad")["status"], "error")
            self.assertEqual(store.get_item_state("good")["status"], "success")
        finally:
            store.close()


class CrawlShopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "items.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, max_items=100, reset=False):
        return CrawlerConfig(
            key="demo-key",
            secret="demo-secret",
            seller_id="2200684271326",
            shop_id="517932711",
            max_items=max_items,
            db_path=self.db_path,
            reset=reset,
            delay=0,
        )

    def page_response(self, page, page_count=3, count=2):
        return {
            "items": {
                "shop_id": "517932711",
                "page": str(page),
                "page_count": page_count,
                "total_results": page_count * count,
                "real_total_results": page_count * count,
                "item": [
                    {
                        "num_iid": int(f"{page}{index:03d}"),
                        "title": f"item {page}-{index}",
                        "price": "1.00",
                        "promotion_price": "1.00",
                        "seller_id": "2200684271326",
                        "shop_id": "517932711",
                    }
                    for index in range(count)
                ],
                "page_size": count,
            },
            "error_code": "0000",
        }

    def test_crawl_shop_stops_when_max_items_is_reached(self):
        requested_pages = []

        def fetcher(config, page):
            requested_pages.append(page)
            return self.page_response(page, page_count=10, count=2)

        result = crawl_shop(self.config(max_items=3), fetcher=fetcher)

        self.assertEqual(requested_pages, [1, 2])
        self.assertEqual(result.saved_items, 4)
        self.assertEqual(result.status, "max_items_reached")

    def test_crawl_shop_stops_after_page_count(self):
        requested_pages = []

        def fetcher(config, page):
            requested_pages.append(page)
            return self.page_response(page, page_count=2, count=1)

        result = crawl_shop(self.config(max_items=10), fetcher=fetcher)

        self.assertEqual(requested_pages, [1, 2])
        self.assertEqual(result.saved_items, 2)
        self.assertEqual(result.status, "finished")

    def test_crawl_shop_resumes_by_shop_id_even_when_seller_id_changes(self):
        first_pages = []

        def first_fetcher(config, page):
            first_pages.append(page)
            return self.page_response(page, page_count=5, count=1)

        first_result = crawl_shop(self.config(max_items=2), fetcher=first_fetcher)
        self.assertEqual(first_result.status, "max_items_reached")

        second_pages = []
        config = self.config(max_items=4)
        config.seller_id = "different-seller"

        def second_fetcher(config, page):
            second_pages.append(page)
            return self.page_response(page, page_count=5, count=1)

        second_result = crawl_shop(config, fetcher=second_fetcher)

        self.assertEqual(first_pages, [1, 2])
        self.assertEqual(second_pages, [3, 4])
        self.assertEqual(second_result.saved_items, 4)

    def test_crawl_shop_stops_when_next_page_repeats_same_items(self):
        requested_pages = []

        def fetcher(config, page):
            requested_pages.append(page)
            if page == 1:
                return self.page_response(page, page_count=10, count=2)
            return {
                "items": {
                    "shop_id": "517932711",
                    "page": str(page),
                    "page_count": 10,
                    "total_results": 20,
                    "real_total_results": 20,
                    "item": [
                        {
                            "num_iid": 2000,
                            "title": "duplicate 0",
                            "price": "1.00",
                            "seller_id": "2200684271326",
                            "shop_id": "517932711",
                        },
                        {
                            "num_iid": 2001,
                            "title": "duplicate 1",
                            "price": "1.00",
                            "seller_id": "2200684271326",
                            "shop_id": "517932711",
                        },
                    ],
                    "page_size": 2,
                },
                "error_code": "0000",
            }

        def first_page_response(page, page_count=10, count=2):
            return {
                "items": {
                    "shop_id": "517932711",
                    "page": str(page),
                    "page_count": page_count,
                    "total_results": 20,
                    "real_total_results": 20,
                    "item": [
                        {
                            "num_iid": 2000,
                            "title": "duplicate 0",
                            "price": "1.00",
                            "seller_id": "2200684271326",
                            "shop_id": "517932711",
                        },
                        {
                            "num_iid": 2001,
                            "title": "duplicate 1",
                            "price": "1.00",
                            "seller_id": "2200684271326",
                            "shop_id": "517932711",
                        },
                    ],
                    "page_size": count,
                },
                "error_code": "0000",
            }

        def repeated_fetcher(config, page):
            requested_pages.append(page)
            return first_page_response(page)

        result = crawl_shop(self.config(max_items=10), fetcher=repeated_fetcher)

        self.assertEqual(requested_pages, [1, 2])
        self.assertEqual(result.saved_items, 2)
        self.assertEqual(result.status, "duplicate_page")


class CliAndFetchTests(unittest.TestCase):
    def test_arg_parser_uses_requested_defaults(self):
        parser = build_arg_parser()
        args = parse_cli_args(parser, [])

        self.assertEqual(args.command, "shop")
        self.assertEqual(args.seller_id, "2200684271326")
        self.assertEqual(args.shop_id, "517932711")
        self.assertEqual(args.env, "password.env")
        self.assertEqual(args.db, os.path.join("data", "taobao_shop_items.sqlite3"))

    def test_script_help_runs_when_called_by_file_path(self):
        result = subprocess.run(
            [sys.executable, os.path.join("src", "shop_crawler.py"), "--help"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("shop", result.stdout)
        self.assertIn("item", result.stdout)

    def test_config_from_args_reads_credentials_from_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "password.env"
            env_path.write_text("key=from-env\nsecret=secret-env\n", encoding="utf-8")
            db_path = Path(tmp) / "crawler.sqlite3"

            parser = build_arg_parser()
            args = parse_cli_args(
                parser,
                [
                    "--env",
                    str(env_path),
                    "--db",
                    str(db_path),
                    "--shop-id",
                    "custom-shop",
                    "--max-items",
                    "7",
                ]
            )
            config = config_from_args(args)

        self.assertEqual(config.key, "from-env")
        self.assertEqual(config.secret, "secret-env")
        self.assertEqual(config.shop_id, "custom-shop")
        self.assertEqual(config.max_items, 7)
        self.assertEqual(config.db_path, str(db_path))

    def test_fetch_page_builds_expected_url_and_decodes_json(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return b'{"items":{"item":[]},"error_code":"0000"}'

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return FakeResponse()

        config = CrawlerConfig(
            key="demo-key",
            secret="demo-secret",
            seller_id="seller-1",
            shop_id="shop-1",
            timeout=12,
        )
        response = fetch_page(config, 5, opener=opener)
        query = parse_qs(urlparse(captured["url"]).query)

        self.assertEqual(response["error_code"], "0000")
        self.assertEqual(captured["timeout"], 12)
        self.assertEqual(query["key"], ["demo-key"])
        self.assertEqual(query["secret"], ["demo-secret"])
        self.assertEqual(query["seller_id"], ["seller-1"])
        self.assertEqual(query["shop_id"], ["shop-1"])
        self.assertEqual(query["page"], ["5"])
        self.assertEqual(query["lang"], ["zh-CN"])

    def test_fetch_item_detail_builds_expected_url_and_decodes_json(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return b'{"item":{"num_iid":"520813250866"},"error_code":"0000"}'

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return FakeResponse()

        config = ItemCrawlerConfig(
            key="demo-key",
            secret="demo-secret",
            num_iids=["520813250866"],
            timeout=9,
        )
        response = fetch_item_detail(config, "520813250866", opener=opener)
        query = parse_qs(urlparse(captured["url"]).query)

        self.assertEqual(response["error_code"], "0000")
        self.assertIn("/taobao/item_get_pro/", captured["url"])
        self.assertEqual(captured["timeout"], 9)
        self.assertEqual(query["key"], ["demo-key"])
        self.assertEqual(query["secret"], ["demo-secret"])
        self.assertEqual(query["num_iid"], ["520813250866"])
        self.assertEqual(query["lang"], ["zh-CN"])

    def test_fetch_item_detail_can_use_item_get_endpoint(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return b'{"item":{"num_iid":"652874751412"},"error_code":"0000"}'

        def opener(request, timeout):
            captured["url"] = request.full_url
            return FakeResponse()

        config = ItemCrawlerConfig(
            key="demo-key",
            secret="demo-secret",
            num_iids=["652874751412"],
            item_api="item_get",
            is_promotion="1",
        )
        response = fetch_item_detail(config, "652874751412", opener=opener)
        query = parse_qs(urlparse(captured["url"]).query)

        self.assertEqual(response["item"]["num_iid"], "652874751412")
        self.assertIn("/taobao/item_get/", captured["url"])
        self.assertNotIn("/taobao/item_get_pro/", captured["url"])
        self.assertEqual(query["num_iid"], ["652874751412"])
        self.assertEqual(query["is_promotion"], ["1"])

    def test_config_from_item_args_reads_inline_and_file_num_iids(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "password.env"
            ids_path = Path(tmp) / "ids.txt"
            db_path = Path(tmp) / "crawler.sqlite3"
            env_path.write_text("key=from-env\nsecret=secret-env\n", encoding="utf-8")
            ids_path.write_text("2\n3,1\n", encoding="utf-8")

            parser = build_arg_parser()
            args = parser.parse_args(
                [
                    "item",
                    "--env",
                    str(env_path),
                    "--db",
                    str(db_path),
                    "--num-iids",
                    "1,2",
                    "--num-iids-file",
                    str(ids_path),
                    "--api",
                    "item_get",
                    "--is-promotion",
                    "1",
                    "--reset-items",
                ]
            )
            config = config_from_item_args(args)

        self.assertEqual(config.key, "from-env")
        self.assertEqual(config.secret, "secret-env")
        self.assertEqual(config.num_iids, ["1", "2", "3"])
        self.assertEqual(config.db_path, str(db_path))
        self.assertEqual(config.item_api, "item_get")
        self.assertEqual(config.is_promotion, "1")
        self.assertTrue(config.reset_items)


if __name__ == "__main__":
    unittest.main()
