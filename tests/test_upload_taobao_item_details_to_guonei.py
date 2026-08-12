import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.tools import upload_taobao_item_details_to_guonei as uploader


class GuoneiItemDetailUploadTests(unittest.TestCase):
    def test_build_detail_push_item_maps_suite_images_and_fixed_sort_type(self):
        raw = {
            "error_code": "0000",
            "item": {
                "num_iid": "1001",
                "title": "详情标题",
                "detail_url": "https://item.taobao.com/item.htm?id=1001",
                "pic_url": "//img.alicdn.com/main.jpg",
                "item_imgs": [{"url": "//img.alicdn.com/1.jpg"}, {"url": "https://img.example/2.jpg"}],
            },
        }
        row = {
            "keyword": "润滑液",
            "sort": "_sale",
            "page": 2,
            "num_iid": "1001",
            "title": "详情标题",
            "detail_url": "https://item.taobao.com/item.htm?id=1001",
            "raw_json": json.dumps(raw, ensure_ascii=False),
            "status": "success",
            "last_error": None,
        }

        item = uploader.build_detail_push_item(row)

        self.assertEqual(item["platform"], "淘宝")
        self.assertEqual(item["keyword"], "润滑液")
        self.assertEqual(item["image_type"], "套图")
        self.assertEqual(item["sort_type"], "综合")
        self.assertEqual(item["page_num"], 2)
        self.assertEqual(item["product_title"], "详情标题")
        self.assertEqual(item["image_urls"], ["https://img.alicdn.com/1.jpg", "https://img.example/2.jpg"])
        self.assertEqual(item["crawl_result"]["status"], "success")

    def test_load_detail_source_items_returns_one_record_per_keyword_source(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "items.sqlite3"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE item_detail_sources (
                    keyword TEXT, sort TEXT, page INTEGER, num_iid TEXT, created_at TEXT,
                    PRIMARY KEY (keyword, sort, page, num_iid)
                );
                CREATE TABLE item_details (
                    num_iid TEXT PRIMARY KEY, title TEXT, price TEXT, orginal_price TEXT, nick TEXT,
                    detail_url TEXT, pic_url TEXT, brand TEXT, cid TEXT, seller_id TEXT, shop_id TEXT,
                    sales TEXT, raw_json TEXT NOT NULL, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE item_detail_state (
                    num_iid TEXT PRIMARY KEY, status TEXT, last_error TEXT, created_at TEXT, updated_at TEXT
                );
                """
            )
            raw = json.dumps({"error_code": "0000", "item": {"num_iid": "100", "title": "one", "item_imgs": [{"url": "//img/1.jpg"}]}}, ensure_ascii=False)
            conn.execute("INSERT INTO item_detail_sources VALUES ('润滑液', '', 1, '100', 'now')")
            conn.execute("INSERT INTO item_detail_sources VALUES ('飞机杯', '_sale', 3, '100', 'now')")
            conn.execute("INSERT INTO item_details VALUES ('100', 'one', '', '', '', 'https://item/100', '', '', '', '', '', '', ?, 'now', 'now')", (raw,))
            conn.execute("INSERT INTO item_detail_state VALUES ('100', 'success', NULL, 'now', 'now')")
            conn.commit(); conn.close()

            items = uploader.load_detail_source_items(db_path)

            self.assertEqual(len(items), 2)
            self.assertEqual([item["keyword"] for item in items], ["润滑液", "飞机杯"])
            self.assertEqual([item["sort_type"] for item in items], ["综合", "综合"])
            self.assertEqual([item["image_type"] for item in items], ["套图", "套图"])


    def test_load_detail_source_items_limits_unique_successes_per_keyword(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "items.sqlite3"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE item_detail_sources (
                    keyword TEXT, sort TEXT, page INTEGER, num_iid TEXT, created_at TEXT,
                    PRIMARY KEY (keyword, sort, page, num_iid)
                );
                CREATE TABLE item_details (
                    num_iid TEXT PRIMARY KEY, title TEXT, price TEXT, orginal_price TEXT, nick TEXT,
                    detail_url TEXT, pic_url TEXT, brand TEXT, cid TEXT, seller_id TEXT, shop_id TEXT,
                    sales TEXT, raw_json TEXT NOT NULL, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE item_detail_state (
                    num_iid TEXT PRIMARY KEY, status TEXT, last_error TEXT, created_at TEXT, updated_at TEXT
                );
                """
            )
            for num_iid in ["1", "2", "3"]:
                raw = json.dumps({"item": {"num_iid": num_iid, "title": num_iid, "item_imgs": [{"url": f"//img/{num_iid}.jpg"}]}}, ensure_ascii=False)
                conn.execute("INSERT INTO item_detail_sources VALUES ('润滑液', '', ?, ?, 'now')", (int(num_iid), num_iid))
                conn.execute("INSERT INTO item_details VALUES (?, ?, '', '', '', '', '', '', '', '', '', '', ?, 'now', 'now')", (num_iid, num_iid, raw))
                conn.execute("INSERT INTO item_detail_state VALUES (?, 'success', NULL, 'now', 'now')", (num_iid,))
            conn.commit(); conn.close()

            items = uploader.load_detail_source_items(db_path, per_keyword_limit=2)

            self.assertEqual([item["product_title"] for item in items], ["1", "2"])


    def test_load_detail_source_items_can_filter_by_detail_updated_at(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "items.sqlite3"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE item_detail_sources (keyword TEXT, sort TEXT, page INTEGER, num_iid TEXT, created_at TEXT, PRIMARY KEY (keyword, sort, page, num_iid));
                CREATE TABLE item_details (num_iid TEXT PRIMARY KEY, title TEXT, price TEXT, orginal_price TEXT, nick TEXT, detail_url TEXT, pic_url TEXT, brand TEXT, cid TEXT, seller_id TEXT, shop_id TEXT, sales TEXT, raw_json TEXT NOT NULL, created_at TEXT, updated_at TEXT);
                CREATE TABLE item_detail_state (num_iid TEXT PRIMARY KEY, status TEXT, last_error TEXT, created_at TEXT, updated_at TEXT);
                """
            )
            for num_iid, updated_at in [("old", "2026-07-27T01:00:00+00:00"), ("new", "2026-07-27T09:42:00+00:00")]:
                raw = json.dumps({"item": {"num_iid": num_iid, "title": num_iid, "item_imgs": [{"url": f"//img/{num_iid}.jpg"}]}}, ensure_ascii=False)
                conn.execute("INSERT INTO item_detail_sources VALUES ('润滑液', '', 1, ?, 'now')", (num_iid,))
                conn.execute("INSERT INTO item_details VALUES (?, ?, '', '', '', '', '', '', '', '', '', '', ?, 'now', ?)", (num_iid, num_iid, raw, updated_at))
                conn.execute("INSERT INTO item_detail_state VALUES (?, 'success', NULL, 'now', 'now')", (num_iid,))
            conn.commit(); conn.close()

            items = uploader.load_detail_source_items(db_path, updated_since="2026-07-27T09:41:19+00:00")

            self.assertEqual([item["product_title"] for item in items], ["new"])


    def test_load_detail_source_items_can_filter_by_new_source_created_at(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "items.sqlite3"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE item_detail_sources (keyword TEXT, sort TEXT, page INTEGER, num_iid TEXT, created_at TEXT, PRIMARY KEY (keyword, sort, page, num_iid));
                CREATE TABLE item_details (num_iid TEXT PRIMARY KEY, title TEXT, price TEXT, orginal_price TEXT, nick TEXT, detail_url TEXT, pic_url TEXT, brand TEXT, cid TEXT, seller_id TEXT, shop_id TEXT, sales TEXT, raw_json TEXT NOT NULL, created_at TEXT, updated_at TEXT);
                CREATE TABLE item_detail_state (num_iid TEXT PRIMARY KEY, status TEXT, last_error TEXT, created_at TEXT, updated_at TEXT);
                """
            )
            raw = json.dumps({"item": {"num_iid": "100", "title": "one", "item_imgs": [{"url": "//img/1.jpg"}]}}, ensure_ascii=False)
            conn.execute("INSERT INTO item_details VALUES ('100', 'one', '', '', '', '', '', '', '', '', '', '', ?, 'old', '2026-07-27T01:00:00+00:00')", (raw,))
            conn.execute("INSERT INTO item_detail_state VALUES ('100', 'success', NULL, 'old', 'old')")
            conn.execute("INSERT INTO item_detail_sources VALUES ('旧词', '', 1, '100', '2026-07-27T01:00:00+00:00')")
            conn.execute("INSERT INTO item_detail_sources VALUES ('新词', 'bid', 1, '100', '2026-07-28T01:00:00+00:00')")
            conn.commit(); conn.close()

            items = uploader.load_detail_source_items(db_path, source_created_since="2026-07-28T00:00:00+00:00")

            self.assertEqual([item["keyword"] for item in items], ["新词"])


    def test_incremental_target_total_only_sends_rows_within_final_keyword_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "items.sqlite3"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE item_detail_sources (keyword TEXT, sort TEXT, page INTEGER, num_iid TEXT, created_at TEXT, PRIMARY KEY (keyword, sort, page, num_iid));
                CREATE TABLE item_details (num_iid TEXT PRIMARY KEY, title TEXT, price TEXT, orginal_price TEXT, nick TEXT, detail_url TEXT, pic_url TEXT, brand TEXT, cid TEXT, seller_id TEXT, shop_id TEXT, sales TEXT, raw_json TEXT NOT NULL, created_at TEXT, updated_at TEXT);
                CREATE TABLE item_detail_state (num_iid TEXT PRIMARY KEY, status TEXT, last_error TEXT, created_at TEXT, updated_at TEXT);
                """
            )
            for idx in range(1, 6):
                num_iid = str(idx)
                updated_at = "2026-07-28T01:00:00+00:00" if idx >= 4 else "2026-07-27T01:00:00+00:00"
                raw = json.dumps({"item": {"num_iid": num_iid, "title": num_iid, "item_imgs": [{"url": f"//img/{num_iid}.jpg"}]}}, ensure_ascii=False)
                conn.execute("INSERT INTO item_detail_sources VALUES ('润滑液', '', ?, ?, 'old')", (idx, num_iid))
                conn.execute("INSERT INTO item_details VALUES (?, ?, '', '', '', '', '', '', '', '', '', '', ?, 'old', ?)", (num_iid, num_iid, raw, updated_at))
                conn.execute("INSERT INTO item_detail_state VALUES (?, 'success', NULL, 'old', 'old')", (num_iid,))
            conn.commit(); conn.close()

            items = uploader.load_detail_source_items(
                db_path,
                updated_since="2026-07-28T00:00:00+00:00",
                target_per_keyword_total=4,
            )

            self.assertEqual([item["product_title"] for item in items], ["4"])


if __name__ == "__main__":
    unittest.main()
