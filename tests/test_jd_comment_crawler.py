import sqlite3
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.jd.direct import comment


class JDCommentCrawlerTests(unittest.TestCase):
    def test_fetch_comment_builds_fixed_first_page_request(self):
        captured = {}

        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"code": 0, "data": []}'

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return FakeResponse()

        config = comment.JDCommentCrawlerConfig(token="demo-token", itemids=["2003808"], timeout=9)
        response = comment.fetch_jd_comment(config, "2003808", opener=opener)
        query = parse_qs(urlparse(captured["url"]).query)

        self.assertEqual(response["code"], 0)
        self.assertEqual(query["token"], ["demo-token"])
        self.assertEqual(query["itemid"], ["2003808"])
        self.assertEqual(query["page"], ["1"])
        self.assertEqual(captured["timeout"], 9)

    def test_crawl_saves_response_and_skips_success_on_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "comments.sqlite3")
            config = comment.JDCommentCrawlerConfig(token="token", itemids=["1", "2"], db_path=db_path, delay=0)
            requested = []

            def fetcher(_, itemid):
                requested.append(itemid)
                return {"code": 0, "itemid": itemid, "data": []}

            first = comment.crawl_jd_comments(config, fetcher=fetcher)
            second = comment.crawl_jd_comments(config, fetcher=fetcher)

            self.assertEqual(first.fetched, 2)
            self.assertEqual(second.skipped, 2)
            self.assertEqual(requested, ["1", "2"])
            store = comment.SQLiteJDCommentStore(db_path)
            self.assertEqual(store.get_state("1")["status"], "success")
            self.assertEqual(store.get_comment("2")["page"], 1)
            store.close()

    def test_load_successful_item_ids_reads_only_success_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            detail_db = Path(directory) / "details.sqlite3"
            conn = sqlite3.connect(detail_db)
            conn.executescript("""
                CREATE TABLE jd_item_state (num_iid TEXT PRIMARY KEY, status TEXT NOT NULL);
                INSERT INTO jd_item_state VALUES ('1', 'success');
                INSERT INTO jd_item_state VALUES ('2', 'error');
                INSERT INTO jd_item_state VALUES ('3', 'success');
            """)
            conn.close()

            self.assertEqual(comment.load_successful_item_ids(detail_db), ["1", "3"])


if __name__ == "__main__":
    unittest.main()
