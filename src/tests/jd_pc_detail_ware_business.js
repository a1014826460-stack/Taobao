#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_API_URL = 'https://api.m.jd.com/';
const DEFAULT_FUNCTION_ID = 'pc_detailpage_wareBusiness';
const DEFAULT_APPID = 'pc-item-soa';
const DEFAULT_CLIENT = 'pc';
const DEFAULT_CLIENT_VERSION = '1.0.0';
const DEFAULT_AREA = '19_1666_36264_36271';
const DEFAULT_PAGE_AREA = '1_72_2799_0';
const COOKIE_DOMAINS = ['.jd.com', '.m.jd.com', '.item.jd.com', '.api.m.jd.com', '.360buyimg.com'];

function extractSkuId(input) {
  const text = String(input || '').trim();
  if (!text) throw new Error('skuId is required');
  const direct = text.match(/^\d{6,}$/);
  if (direct) return direct[0];
  const fromUrl = text.match(/(?:item\.jd\.com\/|item\.m\.jd\.com\/product\/)(\d+)\.html/i);
  if (fromUrl) return fromUrl[1];
  const anyLongNumber = text.match(/\b(\d{6,})\b/);
  if (anyLongNumber) return anyLongNumber[1];
  throw new Error(`Cannot extract JD skuId from: ${text}`);
}

function sortForJson(value) {
  if (Array.isArray(value)) return value.map(sortForJson);
  if (value && typeof value === 'object') {
    return Object.keys(value).sort().reduce((acc, key) => {
      const item = value[key];
      if (item !== undefined) acc[key] = sortForJson(item);
      return acc;
    }, {});
  }
  return value;
}

function stableJsonStringify(value) {
  return JSON.stringify(sortForJson(value));
}

function buildWareBusinessBody(options) {
  const skuId = extractSkuId(options && options.skuId);
  const area = String((options && options.area) || DEFAULT_AREA);
  return {
    skuId,
    cat: String((options && options.cat) || ''),
    area,
    shopId: String((options && options.shopId) || ''),
    venderId: String((options && options.venderId) || ''),
    paramJson: String((options && options.paramJson) || ''),
    num: Number((options && options.num) || 1),
    bbTraffic: '',
    canvasType: 1,
    similar: '',
    fromType: 1,
    batchAddCart: '',
    pduid: String((options && options.pduid) || ''),
    p: String((options && options.p) || ''),
    usedPin: String((options && options.usedPin) || ''),
    freeBuyShow: 0,
    couponBatch: '',
    noShopInfo: 0,
    priceArea: area,
    addrId: String((options && options.addrId) || ''),
    supportDefaultAddress: 0,
  };
}

function buildPageWareBusinessBody(options) {
  const skuId = extractSkuId(options && options.skuId);
  const area = String((options && options.area) || DEFAULT_PAGE_AREA);
  return {
    skuId,
    area,
    num: String((options && options.num) || 1),
    sfTime: String((options && options.sfTime) || '1,0,0'),
  };
}

function buildUnsignedApiUrl(params) {
  const url = new URL(DEFAULT_API_URL);
  const ordered = {
    functionId: params.functionId || DEFAULT_FUNCTION_ID,
    body: params.body,
    h5st: params.h5st,
    uuid: params.uuid,
    loginType: params.loginType || '3',
    appid: params.appid || DEFAULT_APPID,
    clientVersion: params.clientVersion || DEFAULT_CLIENT_VERSION,
    client: params.client || DEFAULT_CLIENT,
    t: params.t || String(Date.now()),
    'x-api-eid-token': params.eidToken,
    scval: params.scval,
  };
  for (const [key, value] of Object.entries(ordered)) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value));
  }
  return url.toString();
}

function parseCookieHeader(cookieHeader) {
  return String(cookieHeader || '')
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const index = part.indexOf('=');
      if (index < 0) return null;
      return { name: part.slice(0, index).trim(), value: part.slice(index + 1).trim() };
    })
    .filter((item) => item && item.name);
}

function cookieObjectsForDomains(name, value) {
  return COOKIE_DOMAINS.map((domain) => ({
    name,
    value,
    domain,
    path: '/',
    httpOnly: false,
    secure: true,
    sameSite: 'Lax',
  }));
}

function cookiesForPlaywright(cookieHeader) {
  const result = [];
  for (const cookie of parseCookieHeader(cookieHeader)) {
    result.push(...cookieObjectsForDomains(cookie.name, cookie.value));
  }
  return result;
}

function extractSdtokenFromRpHeader(headerValue) {
  const parts = String(headerValue || '').split(';');
  if (parts.length >= 3 && parts[0] === 'set') return parts.slice(2).join(';').trim();
  return '';
}

function parseArgs(argv) {
  const args = {
    skuId: '',
    area: DEFAULT_AREA,
    pageArea: '',
    outputDir: path.join('data', 'jd_reverse', 'items'),
    headless: true,
    cookie: process.env.JD_COOKIE || '',
    timeout: 60000,
    saveHtml: false,
    captureOnly: false,
    debug: false,
    noSdtokenRetry: false,
    stealthMode: 'launch',
  };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === '--area') args.area = argv[++i];
    else if (token === '--page-area') args.pageArea = argv[++i];
    else if (token === '--output-dir') args.outputDir = argv[++i];
    else if (token === '--cookie') args.cookie = argv[++i];
    else if (token === '--headed') args.headless = false;
    else if (token === '--headless') args.headless = true;
    else if (token === '--timeout') args.timeout = Number(argv[++i]);
    else if (token === '--save-html') args.saveHtml = true;
    else if (token === '--capture-only') args.captureOnly = true;
    else if (token === '--debug') args.debug = true;
    else if (token === '--no-sdtoken-retry') args.noSdtokenRetry = true;
    else if (token === '--stealth-js') args.stealthMode = 'js';
    else if (token === '--no-stealth') args.stealthMode = 'none';
    else if (token === '-h' || token === '--help') args.help = true;
    else if (!args.skuId) args.skuId = token;
    else throw new Error(`Unknown argument: ${token}`);
  }
  if (args.skuId) args.skuId = extractSkuId(args.skuId);
  return args;
}

function usage() {
  return `Usage:\n  node src/tests/jd_pc_detail_ware_business.js <skuId|item-url> [--area 19_1666_36264_36271] [--page-area 1_72_2799_0] [--output-dir data/jd_reverse/items] [--headed] [--debug] [--stealth-js] [--no-stealth]\n\nCookie:\n  PowerShell: $env:JD_COOKIE='your jd cookie'; node src/tests/jd_pc_detail_ware_business.js 10207466352379\n`;
}

function redact(text, cookie) {
  let output = String(text || '');
  if (cookie) output = output.split(cookie).join('[REDACTED_JD_COOKIE]');
  return output.replace(/(pt_key=)[^;\s]+/g, '$1[REDACTED]').replace(/(thor=)[^;\s]+/g, '$1[REDACTED]');
}

async function waitForCapturedWareBusiness(page, skuId, timeout) {
  return page.waitForResponse(
    (res) => {
      const url = res.url();
      return url.includes('functionId=pc_detailpage_wareBusiness') && url.includes(encodeURIComponent(skuId));
    },
    { timeout }
  ).catch(() => null);
}

async function signWithPage(page, params) {
  return page.evaluate(async (input) => {
    const pSign = window.PSign;
    if (!pSign || typeof pSign.sign !== 'function') throw new Error('window.PSign.sign is unavailable');
    const signPayload = {
      appid: input.appid,
      appId: input.appid,
      functionId: input.functionId,
      body: input.bodyObject,
      client: input.client,
      clientVersion: input.clientVersion,
      t: input.t,
    };
    let signed = await pSign.sign(signPayload);
    if (!signed && typeof pSign.signSync === 'function') signed = pSign.signSync(signPayload);
    return signed;
  }, params);
}

function normalizeSignedParams(signed) {
  if (!signed) throw new Error('PSign returned empty result');
  if (typeof signed === 'string') {
    const query = signed.includes('?') ? signed.slice(signed.indexOf('?') + 1) : signed;
    return Object.fromEntries(new URLSearchParams(query));
  }
  if (signed.body && signed.h5st) return signed;
  if (signed.params) return signed.params;
  if (signed.data) return signed.data;
  return signed;
}


async function applyStealth(context) {
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    window.chrome = window.chrome || { runtime: {} };
    const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
    if (originalQuery) {
      window.navigator.permissions.query = (parameters) => (
        parameters && parameters.name === 'notifications'
          ? Promise.resolve({ state: Notification.permission })
          : originalQuery(parameters)
      );
    }
  });
}

async function browserDiagnostics(page) {
  return page.evaluate(() => ({
    href: location.href,
    readyState: document.readyState,
    hasPSign: !!window.PSign,
    webdriver: navigator.webdriver,
    cookieNames: document.cookie.split(';').map((s) => s.trim().split('=')[0]).filter(Boolean).sort(),
    userAgent: navigator.userAgent,
  })).catch((error) => ({ error: String(error && error.message || error) }));
}

async function captureWareBusinessOnce(context, args, attempt) {
  const page = await context.newPage();
  page.setDefaultTimeout(args.timeout);
  const pageUrl = `https://item.jd.com/${args.skuId}.html`;
  let capturedUrl = '';
  let capturedStatus = 0;
  let capturedText = '';
  let capturedHeaders = {};
  let signedParams = null;

  page.on('response', async (res) => {
    const url = res.url();
    if (url.includes('functionId=pc_detailpage_wareBusiness') && !capturedUrl) {
      capturedUrl = url;
      capturedStatus = res.status();
      capturedHeaders = await res.allHeaders().catch(() => ({}));
      try { capturedText = await res.text(); } catch (_) {}
    }
  });

  const responsePromise = waitForCapturedWareBusiness(page, args.skuId, Math.min(args.timeout, 30000));
  await page.goto(pageUrl, { waitUntil: 'commit', timeout: args.timeout }).catch(() => null);
  await page.waitForLoadState('domcontentloaded', { timeout: args.timeout }).catch(() => null);
  const capturedResponse = await responsePromise;
  if (capturedResponse && !capturedText) {
    capturedUrl = capturedResponse.url();
    capturedStatus = capturedResponse.status();
    capturedHeaders = await capturedResponse.allHeaders().catch(() => ({}));
    try { capturedText = await capturedResponse.text(); } catch (_) {}
  }

  if (!capturedUrl || args.captureOnly) {
    await page.waitForFunction(() => !!(window.PSign && window.PSign.sign), null, { timeout: args.timeout });
    const bodyObject = buildPageWareBusinessBody({ skuId: args.skuId, area: args.pageArea || DEFAULT_PAGE_AREA });
    const t = String(Date.now());
    signedParams = normalizeSignedParams(await signWithPage(page, {
      appid: DEFAULT_APPID,
      functionId: DEFAULT_FUNCTION_ID,
      bodyObject,
      client: DEFAULT_CLIENT,
      clientVersion: DEFAULT_CLIENT_VERSION,
      t,
    }));
    capturedUrl = buildUnsignedApiUrl({
      functionId: DEFAULT_FUNCTION_ID,
      body: typeof signedParams.body === 'string' ? signedParams.body : JSON.stringify(bodyObject),
      h5st: signedParams.h5st,
      uuid: signedParams.uuid || await page.evaluate(() => (document.cookie.match(/__jdu=([^;]+)/)?.[1] || '')),
      loginType: signedParams.loginType || '3',
      appid: signedParams.appid || DEFAULT_APPID,
      clientVersion: signedParams.clientVersion || DEFAULT_CLIENT_VERSION,
      client: signedParams.client || DEFAULT_CLIENT,
      t: signedParams.t || t,
      eidToken: signedParams['x-api-eid-token'] || await page.evaluate(() => document.cookie.match(/3AB9D23F7A4B3CSS=([^;]+)/)?.[1] || ''),
      scval: args.skuId,
    });
    const apiResp = await context.request.get(capturedUrl, {
      headers: { Referer: pageUrl, Origin: 'https://item.jd.com', Accept: 'application/json,text/plain,*/*' },
      timeout: args.timeout,
    });
    capturedStatus = apiResp.status();
    capturedHeaders = apiResp.headers();
    capturedText = await apiResp.text();
  }

  return {
    attempt,
    page,
    pageUrl,
    url: capturedUrl,
    status: capturedStatus,
    text: capturedText,
    headers: capturedHeaders,
    signedParams,
    diagnostics: args.debug ? await browserDiagnostics(page) : undefined,
  };
}

async function run(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.help || !args.skuId) {
    console.log(usage());
    return args.help ? 0 : 1;
  }

  const { chromium } = require('playwright');
  fs.mkdirSync(args.outputDir, { recursive: true });
  const launchOptions = { headless: args.headless };
  if (args.stealthMode === 'launch' || args.stealthMode === 'js') {
    launchOptions.args = ['--disable-blink-features=AutomationControlled'];
    launchOptions.ignoreDefaultArgs = ['--enable-automation'];
  }
  const browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    extraHTTPHeaders: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    },
  });
  if (args.stealthMode === 'js') await applyStealth(context);
  if (args.cookie) await context.addCookies(cookiesForPlaywright(args.cookie));

  let result = await captureWareBusinessOnce(context, args, 1);
  let retrySdtoken = '';
  if (result.status === 403 && !args.noSdtokenRetry) {
    retrySdtoken = extractSdtokenFromRpHeader(result.headers['x-rp-sdtoken'] || result.headers['X-Rp-Sdtoken']);
    if (retrySdtoken) {
      await context.addCookies(cookieObjectsForDomains('sdtoken', retrySdtoken));
      await result.page.close().catch(() => null);
      result = await captureWareBusinessOnce(context, args, 2);
    }
  }

  let parsed = null;
  try { parsed = JSON.parse(result.text); } catch (_) {}
  const outPath = path.join(args.outputDir, `${args.skuId}.wareBusiness.json`);
  const payload = {
    skuId: args.skuId,
    fetchedAt: new Date().toISOString(),
    status: result.status,
    attempt: result.attempt,
    sdtokenRetried: Boolean(retrySdtoken),
    url: result.url,
    responseHeaders: result.headers,
    diagnostics: result.diagnostics,
    signedParams: result.signedParams,
    response: parsed || result.text,
  };
  fs.writeFileSync(outPath, JSON.stringify(payload, null, 2), 'utf8');

  console.log(`Saved: ${outPath}`);
  console.log(`HTTP status: ${result.status}`);
  console.log(`Attempt: ${result.attempt}${retrySdtoken ? ' (sdtoken refreshed once)' : ''}`);
  if (args.debug) console.log('Diagnostics saved in output JSON.');
  console.log(`API URL: ${redact(result.url, args.cookie).slice(0, 1200)}${result.url.length > 1200 ? '...' : ''}`);
  if (parsed) {
    const data = parsed.data || parsed.result || parsed;
    console.log('JSON keys:', Object.keys(parsed).slice(0, 30).join(', '));
    if (data && typeof data === 'object') {
      const summary = {};
      for (const key of ['skuId', 'wareInfo', 'price', 'stock', 'shopInfo', 'vender', 'isLogin', 'code', 'message']) {
        if (data[key] !== undefined) summary[key] = data[key];
      }
      console.log('Summary:', JSON.stringify(summary).slice(0, 1000));
    }
  } else {
    console.log('Response preview:', redact(result.text, args.cookie).slice(0, 1000));
  }

  if (args.saveHtml) fs.writeFileSync(path.join(args.outputDir, `${args.skuId}.page.html`), await result.page.content(), 'utf8');
  await browser.close();
  return result.status >= 200 && result.status < 500 ? 0 : 1;
}

if (require.main === module) {
  run().then(
    (code) => process.exit(code),
    (error) => {
      console.error(redact(`ERROR: ${error && error.stack ? error.stack : error}`, process.env.JD_COOKIE));
      process.exit(1);
    }
  );
}

module.exports = {
  extractSkuId,
  stableJsonStringify,
  buildWareBusinessBody,
  buildPageWareBusinessBody,
  buildUnsignedApiUrl,
  parseCookieHeader,
  cookiesForPlaywright,
  extractSdtokenFromRpHeader,
  parseArgs,
  run,
};
