const test = require('node:test');
const assert = require('node:assert/strict');

const {
  parseBatchIds,
  parseArgs,
  randomDelayMs,
  shouldStopForStatus,
} = require('../src/tests/jd_ware_business_batch.js');

test('parseBatchIds deduplicates whitespace and comma separated sku ids', () => {
  assert.deepEqual(parseBatchIds(['100, 101\n100', '102']), ['100', '101', '102']);
});

test('parseArgs defaults to random 10-30 second delay and expected output paths', () => {
  const args = parseArgs(['--ids', '100 101']);
  assert.deepEqual(args.skuIds, ['100', '101']);
  assert.equal(args.delayMinMs, 10000);
  assert.equal(args.delayMaxMs, 30000);
  assert.equal(args.stopOn403, true);
  assert.equal(args.db, 'data/jd_ware_business_details.sqlite3');
  assert.equal(args.xlsx, 'data/jd_ware_business_details.xlsx');
});

test('parseArgs supports explicit random delay bounds', () => {
  const args = parseArgs(['--ids', '100', '--delay-min', '3', '--delay-max', '9']);
  assert.equal(args.delayMinMs, 3000);
  assert.equal(args.delayMaxMs, 9000);
});

test('randomDelayMs returns inclusive bounded integer milliseconds', () => {
  for (let i = 0; i < 50; i += 1) {
    const value = randomDelayMs(10000, 30000);
    assert.equal(Number.isInteger(value), true);
    assert.equal(value >= 10000, true);
    assert.equal(value <= 30000, true);
  }
});

test('shouldStopForStatus stops on 403 only when enabled', () => {
  assert.equal(shouldStopForStatus(403, true), true);
  assert.equal(shouldStopForStatus(200, true), false);
  assert.equal(shouldStopForStatus(403, false), false);
});
