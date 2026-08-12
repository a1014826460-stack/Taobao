import unittest
from unittest.mock import patch

from src.tools import topup_taobao_item_details as topup
from src.taobao.direct.item import ItemCrawlerConfig


class TopupTaobaoItemDetailsTests(unittest.TestCase):
    def test_crawl_one_stops_immediately_on_4016_without_item_get_pro(self):
        config = ItemCrawlerConfig(key="key", secret="secret", num_iids=[], retries=3, item_api="item_get")
        calls = []

        def fake_fetch(crawler_config, num_iid):
            calls.append(crawler_config.item_api)
            return {"error_code": "4016", "reason": "Key[t3727744565]已欠费"}

        with patch.object(topup, "fetch_item_detail", side_effect=fake_fetch):
            with self.assertRaises(topup.BillingAuthError):
                topup.crawl_one(config, "100")

        self.assertEqual(calls, ["item_get"])


    def test_crawl_one_tries_item_get_three_times_before_item_get_pro_on_api_errors(self):
        config = ItemCrawlerConfig(key="key", secret="secret", num_iids=[], retries=3, item_api="item_get")
        calls = []

        def fake_fetch(crawler_config, num_iid):
            calls.append(crawler_config.item_api)
            if crawler_config.item_api == "item_get":
                return {"error_code": "5000", "reason": "temporary risk"}
            return {"error_code": "0000", "item": {"num_iid": num_iid, "title": "ok"}}

        with patch.object(topup, "fetch_item_detail", side_effect=fake_fetch):
            num_iid, status, payload = topup.crawl_one(config, "100")

        self.assertEqual(num_iid, "100")
        self.assertEqual(status, "success")
        self.assertEqual(payload["item"]["num_iid"], "100")
        self.assertEqual(calls, ["item_get", "item_get", "item_get", "item_get_pro"])

    def test_crawl_one_tries_item_get_pro_three_times_after_item_get_fails(self):
        config = ItemCrawlerConfig(key="key", secret="secret", num_iids=[], retries=3, item_api="item_get")
        calls = []

        def fake_fetch(crawler_config, num_iid):
            calls.append(crawler_config.item_api)
            return {"error_code": "5000", "reason": "temporary risk"}

        with patch.object(topup, "fetch_item_detail", side_effect=fake_fetch):
            num_iid, status, payload = topup.crawl_one(config, "100")

        self.assertEqual(num_iid, "100")
        self.assertEqual(status, "blocked_5000_pro")
        self.assertEqual(calls, ["item_get", "item_get", "item_get", "item_get_pro", "item_get_pro", "item_get_pro"])

    def test_topup_retry_errors_skips_rows_with_prior_4016_error(self):
        import argparse
        import json
        import os
        import sqlite3
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            search_db = Path(directory) / "search.sqlite3"
            item_db = Path(directory) / "items.sqlite3"
            conn = sqlite3.connect(search_db)
            conn.execute(
                """
                CREATE TABLE search_pages (
                    query_fingerprint TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    item_count INTEGER NOT NULL,
                    page_count INTEGER,
                    total_results INTEGER,
                    raw_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (query_fingerprint, page)
                )
                """
            )
            payload = {"items": {"item": [{"num_iid": "old4016"}, {"num_iid": "queued"}]}}
            conn.execute(
                "INSERT INTO search_pages VALUES (?, 1, 2, 1, 2, ?, 'now', 'now')",
                (json.dumps({"q": "高潮液", "sort": ""}, ensure_ascii=False, sort_keys=True), json.dumps(payload, ensure_ascii=False)),
            )
            conn.commit(); conn.close()

            store = topup.SQLiteItemStore(item_db)
            store.mark_error("old4016", ValueError("API returned error_code=4016: Key已欠费"))
            store.mark_pending("queued")
            store.close()

            calls = []
            def fake_fetch(crawler_config, num_iid):
                calls.append(num_iid)
                return {"error_code": "0000", "item": {"num_iid": num_iid, "title": num_iid}}

            args = argparse.Namespace(
                search_db=str(search_db), db=str(item_db), target=2, keyword=["高潮液"], sort=[""],
                workers=1, delay=0, timeout=1, retries=3, item_api="item_get", lang="zh-CN",
                reset=False, retry_errors=True, retry_503=False,
            )
            old_key, old_secret = os.environ.get("FANB_API_KEY"), os.environ.get("FANB_API_SECRET")
            os.environ["FANB_API_KEY"] = "key"; os.environ["FANB_API_SECRET"] = "secret"
            try:
                with patch.object(topup, "fetch_item_detail", side_effect=fake_fetch):
                    topup.topup(args)
            finally:
                if old_key is None: os.environ.pop("FANB_API_KEY", None)
                else: os.environ["FANB_API_KEY"] = old_key
                if old_secret is None: os.environ.pop("FANB_API_SECRET", None)
                else: os.environ["FANB_API_SECRET"] = old_secret

            self.assertEqual(calls, ["queued"])


if __name__ == "__main__":
    unittest.main()



