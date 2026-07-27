import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.tools import upload_taobao_search_to_guonei as uploader


class GuoneiUploadTests(unittest.TestCase):
    def test_build_push_item_maps_search_data_to_documented_fields(self):
        row = {
            "query_fingerprint": json.dumps({"q": "润滑液", "sort": "_sale"}),
            "num_iid": "1001",
            "title": "测试标题",
            "pic_url": "https://img.example/1001.jpg",
            "detail_url": "https://item.taobao.com/item.htm?id=1001",
            "last_seen_page": 3,
            "raw_json": '{"num_iid":"1001"}',
        }

        item = uploader.build_push_item(row)

        self.assertEqual(item["platform"], "淘宝")
        self.assertEqual(item["keyword"], "润滑液")
        self.assertEqual(item["image_type"], "首图")
        self.assertEqual(item["sort_type"], "销量")
        self.assertEqual(item["page_num"], 3)
        self.assertEqual(item["image_urls"], ["https://img.example/1001.jpg"])
        self.assertEqual(item["crawl_result"], {"num_iid": "1001"})

    def test_build_push_item_maps_star_bid_sort_to_sales(self):
        row = {
            "query_fingerprint": json.dumps({"q": "润滑液", "sort": "*bid*"}),
            "pic_url": "https://img.example/1001.jpg",
            "raw_json": "{}",
        }

        item = uploader.build_push_item(row)

        self.assertEqual(item["sort_type"], "销量")

    def test_load_pending_items_excludes_missing_images_and_prior_successes(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "search.sqlite3"
            db = sqlite3.connect(db_path)
            db.executescript(
                """
                CREATE TABLE search_items (
                    query_fingerprint TEXT, num_iid TEXT, title TEXT, pic_url TEXT,
                    detail_url TEXT, last_seen_page INTEGER, raw_json TEXT,
                    PRIMARY KEY (query_fingerprint, num_iid)
                );
                INSERT INTO search_items VALUES
                    ('{"q":"润滑液","sort":"_sale"}', '1', 'one', 'https://img/1.jpg', 'https://item/1', 1, '{}'),
                    ('{"q":"润滑液","sort":""}', '2', 'two', '', 'https://item/2', 1, '{}');
                """
            )
            db.commit()
            db.close()

            pending = uploader.load_pending_items(db_path)

            self.assertEqual([item["product_title"] for item in pending], ["one"])

    def test_load_pending_items_can_filter_to_one_sort(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "search.sqlite3"
            db = sqlite3.connect(db_path)
            db.executescript(
                """
                CREATE TABLE search_items (
                    query_fingerprint TEXT, num_iid TEXT, title TEXT, pic_url TEXT,
                    detail_url TEXT, last_seen_page INTEGER, raw_json TEXT
                );
                INSERT INTO search_items VALUES
                    ('{"q":"润滑液","sort":"*bid*"}', '1', 'bid', 'https://img/1.jpg', '', 1, '{}'),
                    ('{"q":"润滑液","sort":"credit"}', '2', 'credit', 'https://img/2.jpg', '', 1, '{}');
                """
            )
            db.commit()
            db.close()

            pending = uploader.load_pending_items(db_path, sort="*bid*")

            self.assertEqual([item["product_title"] for item in pending], ["bid"])

    def test_upload_batches_marks_only_fully_successful_batches(self):
        items = [{"product_title": "one"}, {"product_title": "two"}, {"product_title": "three"}]
        posted = []

        def post_json(payload):
            posted.append(payload)
            return {"success": True, "success_count": len(payload["items"]), "failed_count": 0}

        result = uploader.upload_items(items, post_json=post_json, batch_size=2)

        self.assertEqual([len(payload["items"]) for payload in posted], [2, 1])
        self.assertEqual(result.sent_items, 3)
        self.assertEqual(result.failed_items, 0)


if __name__ == "__main__":
    unittest.main()
