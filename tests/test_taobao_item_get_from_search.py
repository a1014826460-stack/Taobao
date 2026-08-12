import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.taobao.direct import item


def search_response(ids):
    return {
        "error_code": "0000",
        "items": {
            "page": 1,
            "page_count": 1,
            "total_results": len(ids),
            "item": [
                {
                    "num_iid": str(num_iid),
                    "title": f"商品 {num_iid}",
                    "detail_url": f"https://item.taobao.com/item.htm?id={num_iid}",
                    "pic_url": "https://img.example/item.jpg",
                }
                for num_iid in ids
            ],
        },
    }


def detail_response(num_iid):
    return {
        "error_code": "0000",
        "item": {
            "num_iid": str(num_iid),
            "title": f"详情 {num_iid}",
            "price": "9.90",
            "detail_url": f"https://item.taobao.com/item.htm?id={num_iid}",
        },
    }


class SearchSeededItemGetTests(unittest.TestCase):
    def test_load_item_ids_from_search_uses_comprehensive_sort_deduped_per_keyword_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "search.sqlite3"
            conn = sqlite3.connect(db_path)
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
            now = "2026-07-27T00:00:00+00:00"
            rows = [
                ({"q": "润滑液", "sort": ""}, 1, search_response(["100", "101", "100", "102"])),
                ({"q": "润滑液", "sort": "_sale"}, 1, search_response(["999"])),
                ({"q": "飞机杯", "sort": ""}, 1, search_response(["200", "201", "202"])),
            ]
            for fp, page, payload in rows:
                conn.execute(
                    "INSERT INTO search_pages VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (json.dumps(fp, ensure_ascii=False, sort_keys=True), page, len(payload["items"]["item"]), 1, len(payload["items"]["item"]), json.dumps(payload, ensure_ascii=False), now, now),
                )
            conn.commit()
            conn.close()

            seeds = item.load_item_ids_from_search(db_path, sort="", per_keyword_limit=2)

            self.assertEqual([seed.keyword for seed in seeds], ["润滑液", "润滑液", "飞机杯", "飞机杯"])
            self.assertEqual([seed.num_iid for seed in seeds], ["100", "101", "200", "201"])



    def test_load_item_ids_from_search_falls_back_across_sorts_to_reach_keyword_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "search.sqlite3"
            conn = sqlite3.connect(db_path)
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
            now = "2026-07-27T00:00:00+00:00"
            rows = [
                ({"q": "润滑液", "sort": ""}, 1, search_response(["100", "101", "102"])),
                ({"q": "润滑液", "sort": "_sale"}, 1, search_response(["101", "103", "104"])),
                ({"q": "润滑液", "sort": "credit"}, 1, search_response(["104", "105"])),
                ({"q": "飞机杯", "sort": ""}, 1, search_response(["200"])),
                ({"q": "飞机杯", "sort": "*bid*"}, 1, search_response(["201", "202"])),
            ]
            for fp, page, payload in rows:
                conn.execute(
                    "INSERT INTO search_pages VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (json.dumps(fp, ensure_ascii=False, sort_keys=True), page, len(payload["items"]["item"]), 1, len(payload["items"]["item"]), json.dumps(payload, ensure_ascii=False), now, now),
                )
            conn.commit()
            conn.close()

            seeds = item.load_item_ids_from_search(db_path, sorts=["", "_sale", "credit", "*bid*"], per_keyword_limit=5)

            self.assertEqual([seed.num_iid for seed in seeds if seed.keyword == "润滑液"], ["100", "101", "102", "103", "104"])
            self.assertEqual([seed.sort for seed in seeds if seed.keyword == "润滑液"], ["", "", "", "_sale", "_sale"])
            self.assertEqual([seed.num_iid for seed in seeds if seed.keyword == "飞机杯"], ["200", "201", "202"])

    def test_crawl_items_concurrent_skips_successful_items_and_records_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "items.sqlite3"
            config = item.ItemCrawlerConfig(
                key="key",
                secret="secret",
                num_iids=["100", "101", "102"],
                db_path=str(db_path),
                max_workers=3,
                delay=0,
                item_api="item_get",
            )
            store = item.SQLiteItemStore(db_path)
            store.save_item_detail("100", detail_response("100"))
            store.close()
            fetched = []

            def fetcher(_, num_iid):
                fetched.append(num_iid)
                if num_iid == "102":
                    raise RuntimeError("gateway failed")
                return detail_response(num_iid)

            result = item.crawl_items(config, fetcher=fetcher)

            self.assertEqual(result.total, 3)
            self.assertEqual(result.skipped, 1)
            self.assertEqual(result.fetched, 1)
            self.assertEqual(result.failed, 1)
            self.assertEqual(sorted(fetched), ["101", "102", "102"])
            conn = sqlite3.connect(db_path)
            self.assertEqual(conn.execute("SELECT status FROM item_detail_state WHERE num_iid = '102'").fetchone()[0], "error")
            conn.close()


    def test_crawl_items_marks_5000_api_errors_as_blocked_and_does_not_retry_them(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "items.sqlite3"
            config = item.ItemCrawlerConfig(
                key="key",
                secret="secret",
                num_iids=["100", "101"],
                db_path=str(db_path),
                max_workers=2,
                delay=0,
                item_api="item_get",
            )
            calls = []

            def fetcher(_, num_iid):
                calls.append(num_iid)
                if num_iid == "100":
                    return {"error_code": "5000", "reason": "error5", "item": {"format_check": "fail"}}
                return detail_response(num_iid)

            first = item.crawl_items(config, fetcher=fetcher)
            second = item.crawl_items(config, fetcher=fetcher)

            self.assertEqual(first.failed, 1)
            self.assertEqual(second.skipped, 2)
            self.assertEqual(calls.count("100"), 2)
            self.assertEqual(calls.count("101"), 1)
            conn = sqlite3.connect(db_path)
            self.assertEqual(conn.execute("SELECT status FROM item_detail_state WHERE num_iid = '100'").fetchone()[0], "blocked_5000_pro")
            conn.close()


    def test_default_fetcher_tries_item_get_pro_after_item_get_5000(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "items.sqlite3"
            config = item.ItemCrawlerConfig(
                key="key", secret="secret", num_iids=["100"], db_path=str(db_path), delay=0, item_api="item_get"
            )
            calls = []

            def fetcher(crawler_config, num_iid):
                calls.append(crawler_config.item_api)
                if crawler_config.item_api == "item_get":
                    return {"error_code": "5000", "reason": "risk", "item": {"format_check": "fail"}}
                return detail_response(num_iid)

            result = item.crawl_items(config, fetcher=fetcher)

            self.assertEqual(calls, ["item_get", "item_get_pro"])
            self.assertEqual(result.fetched, 1)


    def test_default_fetcher_tries_item_get_pro_after_item_get_request_retries_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "items.sqlite3"
            config = item.ItemCrawlerConfig(
                key="key", secret="secret", num_iids=["503"], db_path=str(db_path), delay=0, item_api="item_get"
            )
            calls = []

            def fetcher(crawler_config, num_iid):
                calls.append(crawler_config.item_api)
                if crawler_config.item_api == "item_get":
                    raise RuntimeError("request failed after 3 attempt(s): HTTP Error 503: Service Temporarily Unavailable")
                return detail_response(num_iid)

            result = item.crawl_items(config, fetcher=fetcher)

            self.assertEqual(calls, ["item_get", "item_get_pro"])
            self.assertEqual(result.fetched, 1)
            self.assertEqual(result.failed, 0)

    def test_http_503_after_retries_is_abandoned_and_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "items.sqlite3"
            config = item.ItemCrawlerConfig(
                key="key", secret="secret", num_iids=["503"], db_path=str(db_path), max_workers=1, delay=0
            )
            calls = []

            def fetcher(_, num_iid):
                calls.append(num_iid)
                raise RuntimeError("request failed after 3 attempt(s): HTTP Error 503: Service Temporarily Unavailable")

            first = item.crawl_items(config, fetcher=fetcher)
            second = item.crawl_items(config, fetcher=fetcher)

            self.assertEqual(first.failed, 1)
            self.assertEqual(second.skipped, 1)
            self.assertEqual(calls, ["503"])
            conn = sqlite3.connect(db_path)
            self.assertEqual(conn.execute("SELECT status FROM item_detail_state WHERE num_iid = '503'").fetchone()[0], "abandoned_503")
            conn.close()


    def test_blocked_5000_state_is_retried_with_pro_without_repeating_existing_success(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "items.sqlite3"
            store = item.SQLiteItemStore(db_path)
            store.save_item_detail("ok", detail_response("ok"))
            store.mark_blocked_5000("risk", RuntimeError("API returned error_code=5000"))
            store.close()
            config = item.ItemCrawlerConfig(
                key="key", secret="secret", num_iids=["ok", "risk"], db_path=str(db_path), delay=0, item_api="item_get"
            )
            calls = []

            def fetcher(crawler_config, num_iid):
                calls.append((crawler_config.item_api, num_iid))
                return detail_response(num_iid)

            result = item.crawl_items(config, fetcher=fetcher)

            self.assertEqual(result.skipped, 1)
            self.assertEqual(result.fetched, 1)
            self.assertEqual(calls, [("item_get_pro", "risk")])


if __name__ == "__main__":
    unittest.main()
