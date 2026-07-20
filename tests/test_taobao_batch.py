import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import taobao_batch


class TaobaoBatchTest(unittest.TestCase):
    def test_parse_item_ids_deduplicates_whitespace_and_commas(self):
        self.assertEqual(
            taobao_batch.parse_item_ids(['100, 101\n100', '102']),
            ['100', '101', '102'],
        )

    def test_extract_loader_data_from_inline_ice_context(self):
        html = '''<html><script>!(function () {var a = window.__ICE_APP_CONTEXT__ || {};var b = {"loaderData":{"home":{"data":{"res":{"item":{"itemId":"123","title":"测试商品"},"seller":{"shopName":"测试店"},"priceVO":{"price":{"priceText":"9.9"}}}}}}};for (var k in a) {b[k] = a[k]}window.__ICE_APP_CONTEXT__=b;})();</script></html>'''
        data = taobao_batch.extract_loader_data(html)
        self.assertEqual(data['home']['data']['res']['item']['itemId'], '123')

    def test_build_summary_extracts_common_fields(self):
        loader_data = {
            'home': {'data': {'res': {
                'item': {'itemId': '123', 'title': '测试商品', 'vagueSellCount': '1万+'},
                'seller': {'shopName': '测试店', 'sellerId': 'seller1', 'shopId': 'shop1'},
                'priceVO': {'price': {'priceText': '9.9'}},
            }}}
        }
        summary = taobao_batch.build_summary('123', loader_data)
        self.assertEqual(summary['item_id'], '123')
        self.assertEqual(summary['title'], '测试商品')
        self.assertEqual(summary['shop_name'], '测试店')
        self.assertEqual(summary['price_text'], '9.9')
        self.assertEqual(summary['sell_count'], '1万+')

    def test_sqlite_store_skips_success_and_marks_error(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / 'items.sqlite3'
            store = taobao_batch.TaobaoSQLiteStore(db)
            loader = {'home': {'data': {'res': {'item': {'itemId': '123', 'title': '测试'}}}}}
            store.save_success('123', 200, 'https://detail.tmall.com/item.htm?id=123', '<html></html>', loader)
            self.assertTrue(store.is_success('123'))
            store.mark_error('124', 403, 'forbidden', 'https://detail.tmall.com/item.htm?id=124', '<html>403</html>')
            self.assertFalse(store.is_success('124'))
            counts = dict(store.status_counts())
            self.assertEqual(counts['success'], 1)
            self.assertEqual(counts['error'], 1)
            store.close()

    def test_fetch_item_html_sends_default_taobao_cookies(self):
        class FakeResponse:
            status_code = 200
            url = 'https://detail.tmall.com/item.htm?id=123'
            text = '<html></html>'

        class FakeSession:
            def __init__(self):
                self.kwargs = None

            def get(self, url, **kwargs):
                self.kwargs = kwargs
                return FakeResponse()

        session = FakeSession()
        taobao_batch.fetch_item_html(session, '123', 'addr', 30)
        self.assertIn('cookies', session.kwargs)
        self.assertIn('_m_h5_tk', session.kwargs['cookies'])

    def test_fetch_item_html_uses_cookie_header_from_environment(self):
        class FakeResponse:
            status_code = 200
            url = 'https://detail.tmall.com/item.htm?id=123'
            text = '<html></html>'

        class FakeSession:
            def __init__(self):
                self.kwargs = None

            def get(self, url, **kwargs):
                self.kwargs = kwargs
                return FakeResponse()

        session = FakeSession()
        with mock.patch.dict(os.environ, {'TAOBAO_COOKIE': 'fresh=1; another=2'}, clear=False):
            taobao_batch.fetch_item_html(session, '123', 'addr', 30)
        self.assertEqual(session.kwargs['cookies'], {'fresh': '1', 'another': '2'})

    def test_load_shop_item_ids_reads_unique_ids_from_tmall_shop_database(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / 'shop.sqlite3'
            db = sqlite3.connect(db_path)
            db.executescript('''
                CREATE TABLE tmall_shop_items (
                    shop_url TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    PRIMARY KEY (shop_url, item_id)
                );
                INSERT INTO tmall_shop_items (shop_url, item_id) VALUES
                    ('https://iqoo.tmall.com/search.htm', '1001'),
                    ('https://iqoo.tmall.com/search.htm', '1002'),
                    ('https://other.tmall.com/search.htm', '2001');
            ''')
            db.commit()
            db.close()
            self.assertEqual(
                taobao_batch.load_shop_item_ids(db_path, 'https://iqoo.tmall.com/search.htm'),
                ['1001', '1002'],
            )

    def test_crawl_batch_stops_after_first_failed_item(self):
        class Args:
            positional_ids = ['1001', '1002']
            ids = []
            ids_file = []
            shop_db = None
            shop_url = None
            db = ':memory:'
            output_dir = ''
            address_id = None
            timeout = 30
            delay_min = 0
            delay_max = 0
            reset = False

        with mock.patch.object(
            taobao_batch, 'fetch_item_html', side_effect=RuntimeError('blocked')
        ) as fetch_item_html:
            self.assertEqual(taobao_batch.crawl_batch(Args()), 1)
        self.assertEqual(fetch_item_html.call_count, 1)

    def test_detect_noitem_error_from_html_redirect(self):
        html = '<script>window.location.href = "https://error.item.taobao.com/error/noitem?type=noitem&itemid=123"</script>'
        self.assertEqual(
            taobao_batch.detect_block_or_noitem_error(html, '123'),
            'taobao noitem: item_id=123',
        )

    def test_detect_punish_error_from_html(self):
        html = '<script src="//g.alicdn.com/sd/punish/0.0.1/qrcode.min.js"></script><script src="//g.alicdn.com/bsop-static/sufei-punish/0.1.124/build/main.js"></script>'
        self.assertEqual(
            taobao_batch.detect_block_or_noitem_error(html, '123'),
            'taobao punish/captcha page: item_id=123',
        )


if __name__ == '__main__':
    unittest.main()
