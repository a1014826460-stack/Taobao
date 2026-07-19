#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const { run: crawlOne } = require('./jd_pc_detail_ware_business.js');

const DEFAULT_DB = 'data/jd_ware_business_details.sqlite3';
const DEFAULT_XLSX = 'data/jd_ware_business_details.xlsx';
const DEFAULT_OUTPUT_DIR = 'data/jd_reverse/items';

function parseBatchIds(values) {
  const seen = new Set();
  const result = [];
  for (const value of values || []) {
    for (const part of String(value || '').split(/[\s,]+/)) {
      const id = part.trim().replace(/^\ufeff/, '');
      if (!id || seen.has(id)) continue;
      seen.add(id);
      result.push(id);
    }
  }
  return result;
}

function parseArgs(argv) {
  const args = {
    skuIds: [],
    idsFiles: [],
    delayMinMs: 10000,
    delayMaxMs: 30000,
    stopOn403: true,
    db: DEFAULT_DB,
    xlsx: DEFAULT_XLSX,
    outputDir: DEFAULT_OUTPUT_DIR,
    timeout: 90000,
    debug: false,
    reset: false,
    headless: true,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === '--ids') args.skuIds.push(...parseBatchIds([argv[++i]]));
    else if (token === '--ids-file') args.idsFiles.push(argv[++i]);
    else if (token === '--delay') { const value = Math.round(Number(argv[++i]) * 1000); args.delayMinMs = value; args.delayMaxMs = value; }
    else if (token === '--delay-ms') { const value = Number(argv[++i]); args.delayMinMs = value; args.delayMaxMs = value; }
    else if (token === '--delay-min') args.delayMinMs = Math.round(Number(argv[++i]) * 1000);
    else if (token === '--delay-max') args.delayMaxMs = Math.round(Number(argv[++i]) * 1000);
    else if (token === '--delay-min-ms') args.delayMinMs = Number(argv[++i]);
    else if (token === '--delay-max-ms') args.delayMaxMs = Number(argv[++i]);
    else if (token === '--db') args.db = argv[++i];
    else if (token === '--xlsx') args.xlsx = argv[++i];
    else if (token === '--output-dir') args.outputDir = argv[++i];
    else if (token === '--timeout') args.timeout = Number(argv[++i]);
    else if (token === '--debug') args.debug = true;
    else if (token === '--reset') args.reset = true;
    else if (token === '--no-stop-on-403') args.stopOn403 = false;
    else if (token === '--headed') args.headless = false;
    else if (token === '-h' || token === '--help') args.help = true;
    else args.skuIds.push(...parseBatchIds([token]));
  }
  for (const file of args.idsFiles) {
    args.skuIds.push(...parseBatchIds([fs.readFileSync(file, 'utf8')]));
  }
  args.skuIds = parseBatchIds(args.skuIds);
  return args;
}

function usage() {
  return `Usage:\n  node src/tests/jd_ware_business_batch.js --ids-file data/jd_reverse/batch_ids.txt --delay 2 --db data/jd_ware_business_details.sqlite3 --xlsx data/jd_ware_business_details.xlsx\n\nRequires JD_COOKIE environment variable. Default delay is random 10-30 seconds. Stops immediately on HTTP 403 by default.\n`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function randomDelayMs(minMs, maxMs) {
  const min = Math.max(0, Math.min(Number(minMs), Number(maxMs)));
  const max = Math.max(0, Math.max(Number(minMs), Number(maxMs)));
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function shouldStopForStatus(status, enabled) {
  return Boolean(enabled) && Number(status) === 403;
}

function loadState(dbPath) {
  if (!fs.existsSync(dbPath)) return new Map();
  const script = `
import json, sqlite3, sys
conn=sqlite3.connect(sys.argv[1])
try:
 rows=conn.execute("SELECT num_iid,status FROM jd_ware_business_state").fetchall()
 print(json.dumps(rows, ensure_ascii=False))
except sqlite3.OperationalError:
 print('[]')
finally:
 conn.close()
`;
  const result = spawnSync('python', ['-c', script, dbPath], { encoding: 'utf8' });
  if (result.status !== 0) return new Map();
  return new Map(JSON.parse(result.stdout || '[]').map(([id, status]) => [String(id), String(status)]));
}

function saveToSqlite(dbPath, skuId, itemPayload) {
  const tmp = path.join(path.dirname(dbPath), `.tmp_${skuId}_${Date.now()}.json`);
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  fs.writeFileSync(tmp, JSON.stringify(itemPayload), 'utf8');
  const script = `
import json, sys
from src.jd_ware_business_store import SQLiteJDWareBusinessStore
with open(sys.argv[3], 'r', encoding='utf-8') as f:
    payload=json.load(f)
store=SQLiteJDWareBusinessStore(sys.argv[1])
try:
    response=payload.get('response')
    if not isinstance(response, dict):
        store.mark_error(sys.argv[2], 'non-json response', payload.get('status'))
        raise SystemExit(2)
    if int(payload.get('status') or 0) != 200:
        store.mark_error(sys.argv[2], 'http status '+str(payload.get('status')), payload.get('status'))
        raise SystemExit(3)
    store.save_success(sys.argv[2], response, payload.get('url',''), payload.get('status'))
finally:
    store.close()
`;
  const result = spawnSync('python', ['-c', script, dbPath, String(skuId), tmp], { encoding: 'utf8' });
  fs.rmSync(tmp, { force: true });
  if (result.status !== 0) {
    throw new Error(`SQLite save failed for ${skuId}: ${result.stderr || result.stdout}`);
  }
}

function exportXlsx(dbPath, xlsxPath, idsFile) {
  const result = spawnSync('python', [
    'src/jd_ware_business_store.py',
    '--db', dbPath,
    '--output', xlsxPath,
    '--num-iids-file', idsFile,
  ], { encoding: 'utf8' });
  if (result.status !== 0) {
    throw new Error(`XLSX export failed: ${result.stderr || result.stdout}`);
  }
  process.stdout.write(result.stdout);
}

async function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.help || args.skuIds.length === 0) {
    console.log(usage());
    return args.help ? 0 : 1;
  }
  if (!process.env.JD_COOKIE) {
    console.error('ERROR: JD_COOKIE environment variable is required.');
    return 1;
  }

  fs.mkdirSync(args.outputDir, { recursive: true });
  fs.mkdirSync(path.dirname(args.db), { recursive: true });
  const idsFile = path.join(args.outputDir, 'batch_ids.txt');
  fs.writeFileSync(idsFile, args.skuIds.join('\n') + '\n', 'utf8');

  const state = loadState(args.db);
  let fetched = 0;
  let skipped = 0;
  let failed = 0;
  for (let index = 0; index < args.skuIds.length; index += 1) {
    const skuId = args.skuIds[index];
    let attemptedRequest = false;
    if (!args.reset && state.get(skuId) === 'success') {
      skipped += 1;
      console.log(`[${index + 1}/${args.skuIds.length}] skip success ${skuId}`);
    } else {
      attemptedRequest = true;
      console.log(`[${index + 1}/${args.skuIds.length}] crawl ${skuId}`);
      let code = 1;
      try {
        code = await crawlOne([
          skuId,
          '--output-dir', args.outputDir,
          '--timeout', String(args.timeout),
          ...(args.debug ? ['--debug'] : []),
          ...(args.headless ? [] : ['--headed']),
        ]);
      } catch (error) {
        console.error(`ERROR ${skuId}: crawler threw: ${error.message}`);
      }
      const payloadPath = path.join(args.outputDir, `${skuId}.wareBusiness.json`);
      try {
        const payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
        if (shouldStopForStatus(payload.status, args.stopOn403)) {
          console.error(`ALERT ${skuId}: received HTTP 403; stopping batch to avoid further requests.`);
          failed += 1;
          exportXlsx(args.db, args.xlsx, idsFile);
          console.log(`Batch stopped: total=${args.skuIds.length} fetched=${fetched} skipped=${skipped} failed=${failed}`);
          return 2;
        }
        saveToSqlite(args.db, skuId, payload);
        fetched += 1;
      } catch (error) {
        failed += 1;
        console.error(`ERROR ${skuId}: ${error.message}`);
      }
      if (code !== 0) {
        console.error(`WARN ${skuId}: crawler exit code ${code}`);
      }
    }
    if (attemptedRequest && index < args.skuIds.length - 1 && (args.delayMinMs > 0 || args.delayMaxMs > 0)) {
      const waitMs = randomDelayMs(args.delayMinMs, args.delayMaxMs);
      console.log(`wait ${(waitMs / 1000).toFixed(1)}s before next request`);
      await sleep(waitMs);
    }
  }
  exportXlsx(args.db, args.xlsx, idsFile);
  console.log(`Batch finished: total=${args.skuIds.length} fetched=${fetched} skipped=${skipped} failed=${failed}`);
  return failed === 0 ? 0 : 1;
}

if (require.main === module) {
  main().then((code) => process.exit(code), (error) => {
    console.error(`ERROR: ${error && error.stack ? error.stack : error}`);
    process.exit(1);
  });
}

module.exports = {
  parseBatchIds,
  parseArgs,
  randomDelayMs,
  shouldStopForStatus,
  main,
};
