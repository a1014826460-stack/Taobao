import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.tests import taobao_batch


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
