import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.taobao.direct import search


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
                "title": f"item {item_id}",
                "price": "9.90",
                "sales": "10",
                "nick": "shop",
                "detail_url": f"https://item.taobao.com/item.htm?id={item_id}",
                "pic_url": "https://img.example/item.jpg",
            }],
        },
    }


class SearchRequestAndParserTests(unittest.TestCase):
    def test_build_search_request_defaults_to_sales_sort(self):
        config = search.SearchCrawlerConfig(key="key", secret="secret", query="润滑液")

        request = search.build_search_request(config, 2)

        self.assertIn("/taobao/item_search/?", request.full_url)
        self.assertIn("q=%E6%B6%A6%E6%BB%91%E6%B6%B2", request.full_url)
        self.assertIn("page=2", request.full_url)
        self.assertIn("sort=_sale", request.full_url)
        self.assertIn("cache=no", request.full_url)

    def test_parse_search_response_returns_items_and_pagination(self):
        parsed = search.parse_search_response(response_for(2, "1038508552841"))

        self.assertEqual(parsed.items[0]["num_iid"], "1038508552841")
        self.assertEqual(parsed.page, 2)
        self.assertEqual(parsed.page_count, 3)
        self.assertEqual(parsed.total_results, 3)

    def test_parse_search_response_rejects_api_error(self):
        with self.assertRaisesRegex(ValueError, "error_code=1001"):
            search.parse_search_response({"error_code": "1001", "reason": "bad key"})


class SearchStoreTests(unittest.TestCase):
    def test_save_page_upserts_raw_page_item_and_success_state(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "search.sqlite3"
            store = search.SQLiteSearchStore(db_path)
            fingerprint = "test-query"
            store.save_page(fingerprint, 1, response_for(1, "100"))
            changed = response_for(1, "100")
            changed["items"]["item"][0]["title"] = "new title"
            store.save_page(fingerprint, 1, changed)

            self.assertEqual(store.get_page_state(fingerprint, 1)["status"], "success")
            self.assertEqual(store.count_pages(fingerprint), 1)
            self.assertEqual(store.count_items(fingerprint), 1)
            self.assertEqual(store.get_item(fingerprint, "100")["title"], "new title")
            store.close()

    def test_crawl_skips_prior_successful_page_but_retries_error(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "search.sqlite3"
            config = search.SearchCrawlerConfig(
                key="key", secret="secret", query="润滑液", db_path=str(db_path), max_pages=2
            )
            store = search.SQLiteSearchStore(db_path)
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


class SearchConcurrencyTests(unittest.TestCase):
    def test_crawl_fetches_all_requested_pages_and_records_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            config = search.SearchCrawlerConfig(
                key="key", secret="secret", query="润滑液",
                db_path=str(Path(directory) / "search.sqlite3"), max_pages=3, max_workers=3,
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
            self.assertEqual(db.execute("SELECT COUNT(*) FROM search_pages").fetchone()[0], 2)
            self.assertEqual(
                db.execute("SELECT status FROM search_state WHERE page = 2").fetchone()[0], "error"
            )
            db.close()


if __name__ == "__main__":
    unittest.main()
