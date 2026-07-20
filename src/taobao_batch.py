#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Batch Taobao/Tmall item-detail crawler.

The current Tmall PC detail page embeds SSR data in an inline script that assigns
``window.__ICE_APP_CONTEXT__``. Product details live under
``loaderData.home.data.res``. This script fetches the HTML, extracts that JSON,
and stores both normalized fields and raw payload in SQLite.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

try:
    from src.tests.taobao_test import cookies as DEFAULT_COOKIES
except ModuleNotFoundError:  # Allows: python src/taobao_batch.py
    from tests.taobao_test import cookies as DEFAULT_COOKIES

DEFAULT_DB = Path("data/taobao_items.sqlite3")
DEFAULT_OUTPUT_DIR = Path("data/taobao_html")
DEFAULT_ADDRESS_ID = "22802236364"
DEFAULT_DELAY_MIN = 8.0
DEFAULT_DELAY_MAX = 15.0

DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Microsoft Edge";v="150"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
}


def configure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def parse_item_ids(values: Iterable[str] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values or []:
        for part in str(value or "").split():
            for item in part.split(','):
                item_id = item.strip().lstrip('\ufeff')
                if not item_id or item_id in seen:
                    continue
                seen.add(item_id)
                result.append(item_id)
    return result


def build_session() -> requests.Session:
    session = requests.Session()
    # Avoid Windows system proxy such as 127.0.0.1:9000 causing local CA TLS failures.
    session.trust_env = False
    return session


def build_item_url(item_id: str, address_id: str | None = DEFAULT_ADDRESS_ID) -> str:
    params = f"id={item_id}"
    if address_id:
        params = f"addressId={address_id}&" + params
    return "https://detail.tmall.com/item.htm?" + params


def cookies_from_environment() -> dict[str, str]:
    """Use a caller-supplied browser cookie without persisting it in source."""
    cookie_header = os.environ.get('TAOBAO_COOKIE', '').strip()
    if not cookie_header:
        return DEFAULT_COOKIES
    cookies: dict[str, str] = {}
    for segment in cookie_header.split(';'):
        name, separator, value = segment.strip().partition('=')
        if separator and name:
            cookies[name] = value
    return cookies or DEFAULT_COOKIES


def fetch_item_html(session: requests.Session, item_id: str, address_id: str | None, timeout: int) -> tuple[int, str, str]:
    url = build_item_url(item_id, address_id)
    response = session.get(
        url,
        headers=DEFAULT_HEADERS,
        cookies=cookies_from_environment(),
        timeout=timeout,
    )
    return response.status_code, response.url, response.text


def extract_balanced_object(source: str, start_index: int) -> str:
    depth = 0
    in_string = False
    escape = False
    quote = ''
    for index in range(start_index, len(source)):
        char = source[index]
        if in_string:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == quote:
                in_string = False
            continue
        if char in ('"', "'"):
            in_string = True
            quote = char
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return source[start_index:index + 1]
    raise ValueError("unterminated object while extracting __ICE_APP_CONTEXT__")


def extract_ice_context(html: str) -> dict[str, Any]:
    marker = 'var b = '
    marker_index = html.find(marker)
    if marker_index < 0:
        marker = 'var b ='
        marker_index = html.find(marker)
    if marker_index < 0:
        raise ValueError('window.__ICE_APP_CONTEXT__ inline var b object not found')
    object_start = html.find('{', marker_index)
    if object_start < 0:
        raise ValueError('window.__ICE_APP_CONTEXT__ object start not found')
    object_json = extract_balanced_object(html, object_start)
    return json.loads(object_json)


def extract_loader_data(html: str) -> dict[str, Any]:
    context = extract_ice_context(html)
    loader_data = context.get('loaderData')
    if not isinstance(loader_data, dict):
        raise ValueError('loaderData missing or not an object')
    return loader_data


def detect_block_or_noitem_error(html: str, item_id: str) -> str | None:
    if 'error.item.taobao.com/error/noitem' in html or 'type=noitem' in html:
        return f'taobao noitem: item_id={item_id}'
    if 'sufei-punish' in html or '/sd/punish/' in html or 'qrcode.min.js' in html and 'punish' in html:
        return f'taobao punish/captcha page: item_id={item_id}'
    return None


def get_nested(data: dict[str, Any], path: list[str], default: Any = '') -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def build_summary(item_id: str, loader_data: dict[str, Any]) -> dict[str, str]:
    res = get_nested(loader_data, ['home', 'data', 'res'], {})
    if not isinstance(res, dict):
        res = {}
    item = res.get('item') if isinstance(res.get('item'), dict) else {}
    seller = res.get('seller') if isinstance(res.get('seller'), dict) else {}
    price_vo = res.get('priceVO') if isinstance(res.get('priceVO'), dict) else {}
    price = price_vo.get('price') if isinstance(price_vo.get('price'), dict) else {}
    extra_price = price_vo.get('extraPrice') if isinstance(price_vo.get('extraPrice'), dict) else {}
    title_vo = res.get('componentsVO', {}).get('titleVO', {}) if isinstance(res.get('componentsVO'), dict) else {}
    title_obj = title_vo.get('title') if isinstance(title_vo.get('title'), dict) else {}
    title = item.get('title') or item.get('itemTitle') or title_obj.get('title') or ''
    return {
        'item_id': str(item.get('itemId') or item_id),
        'title': str(title or ''),
        'shop_name': str(seller.get('shopName') or seller.get('sellerNick') or ''),
        'seller_id': str(seller.get('sellerId') or seller.get('userId') or ''),
        'shop_id': str(seller.get('shopId') or ''),
        'price_text': str(price.get('priceText') or extra_price.get('priceText') or ''),
        'sell_count': str(item.get('vagueSellCount') or title_vo.get('salesDesc') or ''),
    }


class TaobaoSQLiteStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS taobao_item_details (
                item_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                http_status INTEGER,
                url TEXT,
                title TEXT,
                shop_name TEXT,
                seller_id TEXT,
                shop_id TEXT,
                price_text TEXT,
                sell_count TEXT,
                loader_data_json TEXT,
                raw_html TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def is_success(self, item_id: str) -> bool:
        row = self.conn.execute(
            "SELECT status FROM taobao_item_details WHERE item_id=?",
            (str(item_id),),
        ).fetchone()
        return bool(row and row['status'] == 'success')

    def save_success(self, item_id: str, http_status: int, url: str, raw_html: str, loader_data: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        summary = build_summary(item_id, loader_data)
        self.conn.execute('''
            INSERT INTO taobao_item_details (
                item_id, status, http_status, url, title, shop_name, seller_id, shop_id,
                price_text, sell_count, loader_data_json, raw_html, last_error, created_at, updated_at
            ) VALUES (?, 'success', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                status='success', http_status=excluded.http_status, url=excluded.url,
                title=excluded.title, shop_name=excluded.shop_name, seller_id=excluded.seller_id,
                shop_id=excluded.shop_id, price_text=excluded.price_text, sell_count=excluded.sell_count,
                loader_data_json=excluded.loader_data_json, raw_html=excluded.raw_html,
                last_error=NULL, updated_at=excluded.updated_at
        ''', (
            summary['item_id'], int(http_status), url, summary['title'], summary['shop_name'],
            summary['seller_id'], summary['shop_id'], summary['price_text'], summary['sell_count'],
            json.dumps(loader_data, ensure_ascii=False, separators=(',', ':')), raw_html, now, now,
        ))
        self.conn.commit()

    def mark_error(self, item_id: str, http_status: int | None, error: str, url: str = '', raw_html: str = '') -> None:
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        self.conn.execute('''
            INSERT INTO taobao_item_details (
                item_id, status, http_status, url, title, shop_name, seller_id, shop_id,
                price_text, sell_count, loader_data_json, raw_html, last_error, created_at, updated_at
            ) VALUES (?, 'error', ?, ?, '', '', '', '', '', '', NULL, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                status='error', http_status=excluded.http_status, url=excluded.url,
                raw_html=excluded.raw_html, last_error=excluded.last_error, updated_at=excluded.updated_at
        ''', (str(item_id), http_status, url, raw_html, error, now, now))
        self.conn.commit()

    def status_counts(self) -> list[tuple[str, int]]:
        return [(row[0], row[1]) for row in self.conn.execute(
            "SELECT status, COUNT(*) FROM taobao_item_details GROUP BY status ORDER BY status"
        ).fetchall()]

    def close(self) -> None:
        self.conn.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Batch crawl Taobao/Tmall item detail loaderData into SQLite.')
    parser.add_argument('positional_ids', nargs='*', help='Item IDs separated by whitespace.')
    parser.add_argument('--ids', action='append', default=[], help='Comma/whitespace separated item IDs.')
    parser.add_argument('--ids-file', action='append', default=[], help='Text file containing item IDs.')
    parser.add_argument('--shop-db', help='SQLite database containing tmall_shop_items.')
    parser.add_argument('--shop-url', help='Shop URL used to select IDs from --shop-db.')
    parser.add_argument('--db', default=str(DEFAULT_DB), help='SQLite output path.')
    parser.add_argument('--output-dir', default=str(DEFAULT_OUTPUT_DIR), help='Directory for per-item raw HTML files.')
    parser.add_argument('--address-id', default=DEFAULT_ADDRESS_ID, help='Tmall addressId query parameter.')
    parser.add_argument('--timeout', type=int, default=30)
    parser.add_argument('--delay-min', type=float, default=DEFAULT_DELAY_MIN)
    parser.add_argument('--delay-max', type=float, default=DEFAULT_DELAY_MAX)
    parser.add_argument('--reset', action='store_true', help='Recrawl successful items.')
    return parser.parse_args(argv)


def load_ids(args: argparse.Namespace) -> list[str]:
    values: list[str] = []
    values.extend(args.positional_ids)
    values.extend(args.ids)
    for file_name in args.ids_file:
        values.append(Path(file_name).read_text(encoding='utf-8'))
    if args.shop_db:
        values.extend(load_shop_item_ids(args.shop_db, args.shop_url))
    return parse_item_ids(values)


def load_shop_item_ids(db_path: str | Path, shop_url: str | None = None) -> list[str]:
    """Read product IDs from the Tmall shop crawler's SQLite output."""
    connection = sqlite3.connect(db_path)
    try:
        if shop_url:
            rows = connection.execute(
                'SELECT item_id FROM tmall_shop_items WHERE shop_url = ? ORDER BY item_id',
                (shop_url,),
            ).fetchall()
        else:
            rows = connection.execute(
                'SELECT item_id FROM tmall_shop_items ORDER BY item_id'
            ).fetchall()
    finally:
        connection.close()
    return [str(row[0]) for row in rows]


def random_delay(min_seconds: float, max_seconds: float) -> float:
    low = max(0.0, min(float(min_seconds), float(max_seconds)))
    high = max(0.0, max(float(min_seconds), float(max_seconds)))
    return random.uniform(low, high)


def crawl_batch(args: argparse.Namespace) -> int:
    item_ids = load_ids(args)
    if not item_ids:
        print('ERROR: no item IDs provided', file=sys.stderr)
        return 1
    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    store = TaobaoSQLiteStore(args.db)
    session = build_session()
    fetched = skipped = failed = 0
    try:
        for index, item_id in enumerate(item_ids, start=1):
            if not args.reset and store.is_success(item_id):
                skipped += 1
                print(f'[{index}/{len(item_ids)}] skip success {item_id}')
                continue
            print(f'[{index}/{len(item_ids)}] crawl {item_id}')
            url = build_item_url(item_id, args.address_id)
            raw_html = ''
            try:
                http_status, final_url, raw_html = fetch_item_html(session, item_id, args.address_id, args.timeout)
                if output_dir:
                    html_path = output_dir / f'{item_id}.html'
                    html_path.write_text(raw_html, encoding='utf-8')
                if http_status != 200:
                    raise RuntimeError(f'http status {http_status}')
                block_error = detect_block_or_noitem_error(raw_html, item_id)
                if block_error:
                    raise RuntimeError(block_error)
                loader_data = extract_loader_data(raw_html)
                store.save_success(item_id, http_status, final_url, raw_html, loader_data)
                fetched += 1
                summary = build_summary(item_id, loader_data)
                print(f"  OK title={summary['title'][:60]} price={summary['price_text']} shop={summary['shop_name'][:30]}")
            except Exception as exc:
                failed += 1
                store.mark_error(item_id, None, str(exc), url, raw_html)
                print(f'  ERROR {item_id}: {exc}', file=sys.stderr)
                break
            if index < len(item_ids) and (args.delay_min > 0 or args.delay_max > 0):
                wait = random_delay(args.delay_min, args.delay_max)
                print(f'  wait {wait:.1f}s')
                time.sleep(wait)
    finally:
        counts = store.status_counts()
        store.close()
    print(f'Batch finished: total={len(item_ids)} fetched={fetched} skipped={skipped} failed={failed} counts={counts}')
    return 0 if failed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    configure_stdout_utf8()
    return crawl_batch(parse_args(argv))


if __name__ == '__main__':
    raise SystemExit(main())
