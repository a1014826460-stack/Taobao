import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.jd.direct import search


def response_for(page, item_id=None):
    item_id = item_id or str(page)
    return {
        "error_code": "0000",
        "items": {
            "page": page,
            "page_count": 3,
            "total_results": 3,
            "item": [{
                "num_iid": item_id,
                "title": f"jd item {item_id}",
                "price": "99.00",
                "sales": "10",
                "nick": "jd shop",
                "detail_url": f"https://item.jd.com/{item_id}.html",
                "pic_url": "https://img.example/jd.jpg",
            }],
        },
    }


class JDSearchRequestAndParserTests(unittest.TestCase):
    def test_build_search_request_defaults_to_desc_sales_sort(self):
        config = search.JDSearchCrawlerConfig(key="key", secret="secret", query="手机")

        request = search.build_search_request(config, 2)

        self.assertIn("/jd/item_search/?", request.full_url)
        self.assertIn("q=%E6%89%8B%E6%9C%BA", request.full_url)
        self.assertIn("page=2", request.full_url)
        self.assertIn("sort=_sale", request.full_url)
        self.assertIn("cache=no", request.full_url)

    def test_build_search_request_accepts_supported_sort_values(self):
        for sort in ["bid", "_bid", "_sale", "_review", "_new"]:
            config = search.JDSearchCrawlerConfig(key="key", secret="secret", query="手机", sort=sort)
            self.assertIn(f"sort={sort}", search.build_search_request(config, 1).full_url)

    def test_parse_search_response_returns_items_and_pagination(self):
        parsed = search.parse_search_response(response_for(2, "10025990353889"))

        self.assertEqual(parsed.items[0]["num_iid"], "10025990353889")
        self.assertEqual(parsed.page, 2)
        self.assertEqual(parsed.page_count, 3)
        self.assertEqual(parsed.total_results, 3)

    def test_parse_search_response_rejects_api_error(self):
        with self.assertRaisesRegex(ValueError, "error_code=1001"):
            search.parse_search_response({"error_code": "1001", "reason": "bad key"})


    def test_fetch_search_page_retries_api_error_responses(self):
        calls = []

        class FakeResponse:
            def __init__(self, body):
                self.body = body
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, traceback):
                return False
            def read(self):
                return self.body.encode("utf-8")

        def opener(request, timeout):
            calls.append(request.full_url)
            if len(calls) < 3:
                return FakeResponse('{"error_code":"5000","reason":"data error"}')
            return FakeResponse('{"error_code":"0000","items":{"item":[]}}')

        config = search.JDSearchCrawlerConfig(key="key", secret="secret", query="手机", retries=3)
        response = search.fetch_search_page(config, 1, opener=opener)

        self.assertEqual(response["error_code"], "0000")
        self.assertEqual(len(calls), 3)


    def test_parse_search_response_accepts_error_code_when_items_are_present(self):
        response = response_for(7, "10164994721783")
        response["error_code"] = "5000"
        response["reason"] = "data error,no cache"

        parsed = search.parse_search_response(response)

        self.assertEqual(parsed.items[0]["num_iid"], "10164994721783")
        self.assertEqual(parsed.page, 7)

    def test_fetch_search_page_does_not_retry_error_code_when_items_are_present(self):
        calls = []

        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, traceback):
                return False
            def read(self):
                return b'{"error_code":"5000","reason":"data error,no cache","items":{"page":7,"item":[{"num_iid":"10164994721783"}]}}'

        def opener(request, timeout):
            calls.append(request.full_url)
            return FakeResponse()

        config = search.JDSearchCrawlerConfig(key="key", secret="secret", query="倒模", retries=3)
        response = search.fetch_search_page(config, 7, opener=opener)

        self.assertEqual(response["error_code"], "5000")
        self.assertEqual(len(calls), 1)


class JDSearchStoreAndCrawlTests(unittest.TestCase):
    def test_save_page_upserts_raw_page_item_and_success_state(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "jd_search.sqlite3"
            store = search.SQLiteJDSearchStore(db_path)
            fingerprint = "test-query"
            store.save_page(fingerprint, 1, response_for(1, "100"))
            changed = response_for(1, "100")
            changed["items"]["item"][0]["title"] = "new jd title"
            store.save_page(fingerprint, 1, changed)

            self.assertEqual(store.get_page_state(fingerprint, 1)["status"], "success")
            self.assertEqual(store.count_pages(fingerprint), 1)
            self.assertEqual(store.count_items(fingerprint), 1)
            self.assertEqual(store.get_item(fingerprint, "100")["title"], "new jd title")
            store.close()

    def test_crawl_skips_prior_successful_page_but_retries_error(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "jd_search.sqlite3"
            config = search.JDSearchCrawlerConfig(key="key", secret="secret", query="手机", db_path=str(db_path), max_pages=2)
            store = search.SQLiteJDSearchStore(db_path)
            fingerprint = search.query_fingerprint(config)
            store.save_page(fingerprint, 1, response_for(1))
            store.mark_error(fingerprint, 2, RuntimeError("previous failure"))
            store.close()
            fetched_pages = []

            def fetcher(_, page):
                fetched_pages.append(page)
                return response_for(page)

            result = search.crawl_search(config, fetcher=fetcher)

            self.assertEqual(fetched_pages, [2])
            self.assertEqual(result.skipped_pages, 1)
            self.assertEqual(result.fetched_pages, 1)
            self.assertEqual(result.failed_pages, 0)

    def test_crawl_fetches_all_requested_pages_and_records_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            config = search.JDSearchCrawlerConfig(
                key="key", secret="secret", query="手机",
                db_path=str(Path(directory) / "jd_search.sqlite3"), max_pages=3, max_workers=3,
            )

            def fetcher(_, page):
                if page == 2:
                    raise RuntimeError("gateway failed")
                return response_for(page)

            result = search.crawl_search(config, fetcher=fetcher)

            self.assertEqual(result.requested_pages, 3)
            self.assertEqual(result.fetched_pages, 2)
            self.assertEqual(result.failed_pages, 1)
            self.assertEqual(result.skipped_pages, 0)
            db = sqlite3.connect(config.db_path)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM jd_search_pages").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT status FROM jd_search_state WHERE page = 2").fetchone()[0], "error")
            db.close()


if __name__ == "__main__":
    unittest.main()
