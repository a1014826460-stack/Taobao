import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.jd_item_crawler import (
    JDItemCrawlerConfig,
    SQLiteJDItemStore,
    build_arg_parser,
    config_from_args,
    crawl_jd_items,
    fetch_jd_item_detail,
    load_env,
    parse_cli_args,
    parse_num_iids,
)


class JDInputTests(unittest.TestCase):
    def test_parse_num_iids_accepts_lists_commas_whitespace_and_deduplicates(self):
        values = parse_num_iids(
            ["10025990353889, 100123456789", "10025990353889\n100987654321"]
        )

        self.assertEqual(values, ["10025990353889", "100123456789", "100987654321"])

    def test_parse_num_iids_strips_utf8_bom_from_files(self):
        values = parse_num_iids(["\ufeff10095817869841\n10124273278952"])

        self.assertEqual(values, ["10095817869841", "10124273278952"])


class JDEnvAndConfigTests(unittest.TestCase):
    def test_load_env_reads_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "password.env"
            env_path.write_text(
                "\n# comment\nkey = demo-key\nsecret= demo-secret \n",
                encoding="utf-8",
            )

            values = load_env(env_path)

        self.assertEqual(values["key"], "demo-key")
        self.assertEqual(values["secret"], "demo-secret")

    def test_config_from_args_reads_env_and_item_ids_from_inline_and_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "password.env"
            ids_path = Path(tmp) / "jd_ids.txt"
            db_path = Path(tmp) / "jd.sqlite3"
            env_path.write_text("key=from-env\nsecret=secret-env\n", encoding="utf-8")
            ids_path.write_text("2\n3,1\n", encoding="utf-8")

            parser = build_arg_parser()
            args = parser.parse_args(
                [
                    "--env",
                    str(env_path),
                    "--db",
                    str(db_path),
                    "--num-iids",
                    "1,2",
                    "--num-iids-file",
                    str(ids_path),
                    "--reset-items",
                ]
            )
            config = config_from_args(args)

        self.assertEqual(config.key, "from-env")
        self.assertEqual(config.secret, "secret-env")
        self.assertEqual(config.num_iids, ["1", "2", "3"])
        self.assertEqual(config.db_path, str(db_path))
        self.assertTrue(config.reset_items)


class SQLiteJDItemStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "jd.sqlite3")
        self.store = SQLiteJDItemStore(self.db_path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_save_item_detail_upserts_detail_and_tracks_success_state_by_num_iid(self):
        response = {
            "item": {
                "num_iid": "10025990353889",
                "title": "sample jd item",
                "price": "99.00",
                "orginal_price": "129.00",
                "nick": "jd shop",
                "detail_url": "https://item.jd.com/10025990353889.html",
                "pic_url": "https://img.example.test/jd.jpg",
                "brand": "demo brand",
                "cid": "123",
                "shop_id": "shop-1",
                "sales": 8,
            },
            "error_code": "0000",
        }

        self.store.mark_pending("10025990353889")
        self.store.save_item_detail("10025990353889", response)
        self.store.save_item_detail("10025990353889", response)

        state = self.store.get_item_state("10025990353889")
        detail = self.store.get_item_detail("10025990353889")

        self.assertEqual(state["status"], "success")
        self.assertEqual(detail["num_iid"], "10025990353889")
        self.assertEqual(detail["title"], "sample jd item")
        self.assertEqual(detail["shop_id"], "shop-1")
        self.assertEqual(detail["sales"], "8")
        self.assertEqual(self.store.count_successful(), 1)


class CrawlJDItemsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "jd.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def item_response(self, num_iid):
        return {
            "item": {
                "num_iid": str(num_iid),
                "title": f"jd item {num_iid}",
                "price": "9.90",
                "orginal_price": "19.90",
                "shop_id": "jd-shop",
            },
            "error_code": "0000",
        }

    def config(self, num_iids, reset_items=False):
        return JDItemCrawlerConfig(
            key="demo-key",
            secret="demo-secret",
            num_iids=num_iids,
            db_path=self.db_path,
            reset_items=reset_items,
            delay=0,
        )

    def test_crawl_jd_items_saves_each_detail(self):
        requested = []

        def fetcher(config, num_iid):
            requested.append(num_iid)
            return self.item_response(num_iid)

        result = crawl_jd_items(self.config(["1", "2"]), fetcher=fetcher)

        store = SQLiteJDItemStore(self.db_path)
        try:
            self.assertEqual(requested, ["1", "2"])
            self.assertEqual(result.fetched, 2)
            self.assertEqual(result.skipped, 0)
            self.assertEqual(store.get_item_detail("1")["title"], "jd item 1")
            self.assertEqual(store.get_item_state("2")["status"], "success")
        finally:
            store.close()

    def test_crawl_jd_items_skips_successful_ids_on_resume(self):
        def first_fetcher(config, num_iid):
            return self.item_response(num_iid)

        crawl_jd_items(self.config(["1", "2"]), fetcher=first_fetcher)

        second_requested = []

        def second_fetcher(config, num_iid):
            second_requested.append(num_iid)
            return self.item_response(num_iid)

        result = crawl_jd_items(self.config(["1", "2", "3"]), fetcher=second_fetcher)

        self.assertEqual(second_requested, ["3"])
        self.assertEqual(result.fetched, 1)
        self.assertEqual(result.skipped, 2)

    def test_crawl_jd_items_records_error_and_continues(self):
        def fetcher(config, num_iid):
            if num_iid == "bad":
                raise RuntimeError("boom")
            return self.item_response(num_iid)

        result = crawl_jd_items(self.config(["bad", "good"]), fetcher=fetcher)

        store = SQLiteJDItemStore(self.db_path)
        try:
            self.assertEqual(result.failed, 1)
            self.assertEqual(result.fetched, 1)
            self.assertEqual(store.get_item_state("bad")["status"], "error")
            self.assertEqual(store.get_item_state("good")["status"], "success")
        finally:
            store.close()


class JDFetchAndCliTests(unittest.TestCase):
    def test_fetch_jd_item_detail_builds_expected_url_and_decodes_json(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return b'{"item":{"num_iid":"10025990353889"},"error_code":"0000"}'

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return FakeResponse()

        config = JDItemCrawlerConfig(
            key="demo-key",
            secret="demo-secret",
            num_iids=["10025990353889"],
            timeout=9,
        )
        response = fetch_jd_item_detail(config, "10025990353889", opener=opener)
        query = parse_qs(urlparse(captured["url"]).query)

        self.assertEqual(response["error_code"], "0000")
        self.assertIn("/jd/item_get_pro/", captured["url"])
        self.assertEqual(captured["timeout"], 9)
        self.assertEqual(query["key"], ["demo-key"])
        self.assertEqual(query["secret"], ["demo-secret"])
        self.assertEqual(query["num_iid"], ["10025990353889"])
        self.assertEqual(query["cache"], ["no"])
        self.assertEqual(query["lang"], ["zh-CN"])

    def test_parse_cli_args_requires_num_iids_for_normal_run(self):
        parser = build_arg_parser()

        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parse_cli_args(parser, [])

    def test_script_help_runs_when_called_by_file_path(self):
        result = subprocess.run(
            [sys.executable, os.path.join("src", "jd_item_crawler.py"), "--help"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("JD", result.stdout)
        self.assertIn("--num-iids", result.stdout)


if __name__ == "__main__":
    unittest.main()
