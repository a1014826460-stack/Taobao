const test = require('node:test');
const assert = require('node:assert/strict');

const {
  extractSkuId,
  stableJsonStringify,
  buildWareBusinessBody,
  buildUnsignedApiUrl,
  parseCookieHeader,
  extractSdtokenFromRpHeader,
  parseArgs,
} = require('../src/tests/jd_pc_detail_ware_business.js');

test('extractSkuId accepts raw sku id and JD item URL', () => {
  assert.equal(extractSkuId('10207466352379'), '10207466352379');
  assert.equal(extractSkuId('https://item.jd.com/10207466352379.html'), '10207466352379');
  assert.equal(extractSkuId('https://item.m.jd.com/product/10207466352379.html?foo=bar'), '10207466352379');
});

test('stableJsonStringify recursively sorts object keys without changing arrays', () => {
  const value = { z: 1, a: { y: 2, b: 3 }, list: [{ d: 4, c: 5 }] };
  assert.equal(stableJsonStringify(value), '{"a":{"b":3,"y":2},"list":[{"c":5,"d":4}],"z":1}');
});

test('buildWareBusinessBody creates stable JD PC detail body for a sku id', () => {
  const body = buildWareBusinessBody({ skuId: '10207466352379', area: '19_1666_36264_36271' });
  assert.equal(body.skuId, '10207466352379');
  assert.equal(body.area, '19_1666_36264_36271');
  assert.equal(body.priceArea, '19_1666_36264_36271');
  assert.equal(body.num, 1);
  assert.equal(body.addrId, '');
});

test('buildUnsignedApiUrl encodes required pc_detailpage_wareBusiness query params', () => {
  const url = buildUnsignedApiUrl({
    functionId: 'pc_detailpage_wareBusiness',
    body: '{"skuId":"10207466352379"}',
    appid: 'item-v3',
    client: 'pc',
    clientVersion: '1.0.0',
    t: '1783480000000',
  });
  const parsed = new URL(url);
  assert.equal(parsed.origin + parsed.pathname, 'https://api.m.jd.com/');
  assert.equal(parsed.searchParams.get('functionId'), 'pc_detailpage_wareBusiness');
  assert.equal(parsed.searchParams.get('appid'), 'item-v3');
  assert.equal(parsed.searchParams.get('client'), 'pc');
  assert.equal(parsed.searchParams.get('clientVersion'), '1.0.0');
  assert.equal(parsed.searchParams.get('t'), '1783480000000');
  assert.equal(parsed.searchParams.get('body'), '{"skuId":"10207466352379"}');
});

test('parseCookieHeader handles equals signs and quoted values', () => {
  assert.deepEqual(parseCookieHeader('a=1; token=abc=def,3,990824; RT="z=1&dm=jd.com"'), [
    { name: 'a', value: '1' },
    { name: 'token', value: 'abc=def,3,990824' },
    { name: 'RT', value: '"z=1&dm=jd.com"' },
  ]);
});

test('extractSdtokenFromRpHeader returns token only for set instructions', () => {
  assert.equal(extractSdtokenFromRpHeader('set;1800;ABC_DEF-123'), 'ABC_DEF-123');
  assert.equal(extractSdtokenFromRpHeader('noop;1800;ABC'), '');
  assert.equal(extractSdtokenFromRpHeader(''), '');
});

test('parseArgs uses launch-level stealth by default to avoid prototype pollution', () => {
  assert.equal(parseArgs(['10207466352379']).stealthMode, 'launch');
  assert.equal(parseArgs(['10207466352379', '--stealth-js']).stealthMode, 'js');
  assert.equal(parseArgs(['10207466352379', '--no-stealth']).stealthMode, 'none');
});
