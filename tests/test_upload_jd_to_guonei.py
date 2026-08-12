import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.tools import upload_jd_to_guonei as uploader


class JdGuoneiUploadTests(unittest.TestCase):
    def test_build_search_push_item_maps_jd_fields_and_normalizes_main_image(self):
        row = {
            "query_fingerprint": json.dumps({"q": "跳蛋", "sort": "_sale"}, ensure_ascii=False),
            "num_iid": "1001",
            "title": "京东标题",
            "pic_url": "//img1.360buyimg.com/n6/a.jpg",
            "detail_url": "https://item.jd.com/1001.html",
            "last_seen_page": 7,
            "raw_json": '{"num_iid":"1001"}',
        }

        item = uploader.build_search_push_item(row)

        self.assertEqual(item["platform"], "京东")
        self.assertEqual(item["keyword"], "跳蛋")
        self.assertEqual(item["image_type"], "首图")
        self.assertEqual(item["sort_type"], "销量")
        self.assertEqual(item["page_num"], 7)
        self.assertEqual(item["product_url"], "https://item.jd.com/1001.html")
        self.assertEqual(item["product_title"], "京东标题")
        self.assertEqual(item["image_urls"], ["https://img1.360buyimg.com/n6/a.jpg"])
        self.assertEqual(item["crawl_result"], {"num_iid": "1001"})

    def test_build_detail_push_item_uses_item_images_when_present(self):
        raw = {
            "item": {
                "num_iid": "1002",
                "title": "详情标题",
                "detail_url": "https://item.jd.com/1002.html#crumb-wrap",
                "pic_url": "//img13.360buyimg.com/n12/main.jpg",
                "item_images": [
                    "//img10.360buyimg.com/n1/one.jpg",
                    {"url": "https://img10.360buyimg.com/n1/two.jpg"},
                ],
                "item_imgs": {"item_img": [{"url": "//should-not-use.example/fallback.jpg"}]},
            }
        }
        row = {
            "keyword": "名器",
            "sort": "",
            "page": 2,
            "num_iid": "1002",
            "title": "详情标题",
            "detail_url": "https://item.jd.com/1002.html#crumb-wrap",
            "raw_json": json.dumps(raw, ensure_ascii=False),
            "status": "success",
            "last_error": None,
        }

        item = uploader.build_detail_push_item(row)

        self.assertEqual(item["platform"], "京东")
        self.assertEqual(item["keyword"], "名器")
        self.assertEqual(item["image_type"], "套图")
        self.assertEqual(item["sort_type"], "综合")
        self.assertEqual(item["page_num"], 2)
        self.assertEqual(item["image_urls"], [
            "https://img10.360buyimg.com/n1/one.jpg",
            "https://img10.360buyimg.com/n1/two.jpg",
        ])

    def test_build_detail_push_item_falls_back_to_item_imgs_for_existing_jd_raw_shape(self):
        raw = {
            "item": {
                "num_iid": "1003",
                "title": "详情标题",
                "item_imgs": {"item_img": [
                    {"url": "//img10.360buyimg.com/n1/one.jpg"},
                    {"url": "//img10.360buyimg.com/n1/one.jpg"},
                    {"url": "//img10.360buyimg.com/n1/two.jpg"},
                ]},
            }
        }
        item = uploader.build_detail_push_item({
            "keyword": "跳蛋",
            "sort": "_sale",
            "page": 3,
            "num_iid": "1003",
            "raw_json": json.dumps(raw, ensure_ascii=False),
            "status": "success",
        })

        self.assertEqual(item["image_urls"], [
            "https://img10.360buyimg.com/n1/one.jpg",
            "https://img10.360buyimg.com/n1/two.jpg",
        ])

    def test_load_pending_search_items_uses_state_db_to_skip_successes(self):
        with tempfile.TemporaryDirectory() as directory:
            search_db = Path(directory) / "jd_search.sqlite3"
            state_db = Path(directory) / "upload_state.sqlite3"
            conn = sqlite3.connect(search_db)
            conn.executescript("""
                CREATE TABLE jd_search_items (
                    query_fingerprint TEXT, num_iid TEXT, title TEXT, price TEXT, promotion_price TEXT,
                    sales TEXT, nick TEXT, shop_name TEXT, detail_url TEXT, pic_url TEXT,
                    first_seen_page INTEGER, last_seen_page INTEGER, raw_json TEXT, created_at TEXT, updated_at TEXT
                );
            """)
            conn.execute(
                "INSERT INTO jd_search_items VALUES (?, '1', 'one', '', '', '', '', '', 'https://item/1', 'https://img/1.jpg', 1, 1, '{}', '', '')",
                (json.dumps({"q":"跳蛋","sort":""}, ensure_ascii=False),),
            )
            conn.execute(
                "INSERT INTO jd_search_items VALUES (?, '2', 'two', '', '', '', '', '', 'https://item/2', 'https://img/2.jpg', 1, 1, '{}', '', '')",
                (json.dumps({"q":"跳蛋","sort":""}, ensure_ascii=False),),
            )
            conn.commit(); conn.close()

            uploader.init_upload_state(state_db)
            uploader.mark_uploaded(state_db, ["jd_search:跳蛋::1:1"])

            pending = uploader.load_pending_search_items(search_db, state_db)

            self.assertEqual([item.key for item in pending], ["jd_search:跳蛋::1:2"])

    def test_load_pending_detail_items_joins_sources_and_skips_uploaded_successes(self):
        with tempfile.TemporaryDirectory() as directory:
            detail_db = Path(directory) / "jd_item_details.sqlite3"
            state_db = Path(directory) / "upload_state.sqlite3"
            conn = sqlite3.connect(detail_db)
            conn.executescript("""
                CREATE TABLE jd_item_sources (keyword TEXT, sort TEXT, page INTEGER, num_iid TEXT, created_at TEXT);
                CREATE TABLE jd_item_details (
                    num_iid TEXT PRIMARY KEY, title TEXT, price TEXT, orginal_price TEXT, nick TEXT,
                    detail_url TEXT, pic_url TEXT, brand TEXT, cid TEXT, shop_id TEXT, sales TEXT,
                    raw_json TEXT, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE jd_item_state (num_iid TEXT PRIMARY KEY, status TEXT, last_error TEXT, created_at TEXT, updated_at TEXT);
            """)
            raw = json.dumps({"item":{"num_iid":"100","title":"one","item_imgs":{"item_img":[{"url":"//img/1.jpg"}]}}}, ensure_ascii=False)
            conn.execute("INSERT INTO jd_item_sources VALUES ('跳蛋', '', 1, '100', 'now')")
            conn.execute("INSERT INTO jd_item_sources VALUES ('名器', '_sale', 2, '100', 'now')")
            conn.execute("INSERT INTO jd_item_details VALUES ('100', 'one', '', '', '', 'https://item/100', '', '', '', '', '', ?, 'now', 'now')", (raw,))
            conn.execute("INSERT INTO jd_item_state VALUES ('100', 'success', NULL, 'now', 'now')")
            conn.commit(); conn.close()

            uploader.init_upload_state(state_db)
            uploader.mark_uploaded(state_db, ["jd_detail:跳蛋::1:100"])

            pending = uploader.load_pending_detail_items(detail_db, state_db)

            self.assertEqual([item.key for item in pending], ["jd_detail:名器:_sale:2:100"])
            self.assertEqual(pending[0].payload["keyword"], "名器")

    def test_sort_type_label_only_uses_api_allowed_values(self):
        self.assertEqual(uploader.sort_type_label("_sale"), "销量")
        self.assertEqual(uploader.sort_type_label("bid"), "销量")
        self.assertEqual(uploader.sort_type_label("_new"), "综合")
        self.assertEqual(uploader.sort_type_label("_review"), "综合")
        self.assertEqual(uploader.sort_type_label("unknown"), "综合")

    def test_upload_items_marks_item_level_successes_even_when_batch_success_false(self):
        items = [
            uploader.PendingItem(key="ok", payload={"product_title": "ok"}),
            uploader.PendingItem(key="bad", payload={"product_title": "bad"}),
        ]

        def partial_post(payload):
            return {
                "success": False,
                "success_count": 1,
                "failed_count": 1,
                "results": [
                    {"success": True, "id": 1, "message": "推送成功"},
                    {"success": False, "id": 0, "message": "失败"},
                ],
            }

        with tempfile.TemporaryDirectory() as directory:
            state_db = Path(directory) / "state.sqlite3"
            result = uploader.upload_items(
                items,
                state_db=state_db,
                post_json_func=partial_post,
                batch_size=2,
            )
            conn = sqlite3.connect(state_db)
            states = dict(conn.execute("select upload_key,status from guonei_upload_state"))
            conn.close()

        self.assertEqual(result.sent_items, 1)
        self.assertEqual(result.failed_items, 1)
        self.assertEqual(states, {"ok": "success", "bad": "error"})

    def test_upload_items_stops_after_configured_failed_batches(self):
        items = [uploader.PendingItem(key=f"k{i}", payload={"product_title": str(i)}) for i in range(5)]
        calls = []

        def failing_post(payload):
            calls.append(payload)
            raise OSError("network down")

        with tempfile.TemporaryDirectory() as directory:
            result = uploader.upload_items(
                items,
                state_db=Path(directory) / "state.sqlite3",
                post_json_func=failing_post,
                batch_size=1,
                max_failed_batches=3,
            )

        self.assertEqual(len(calls), 3)
        self.assertEqual(result.failed_items, 3)
        self.assertEqual(result.batches, 3)


if __name__ == "__main__":
    unittest.main()
