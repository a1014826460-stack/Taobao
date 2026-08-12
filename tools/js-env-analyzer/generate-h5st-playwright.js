'use strict';
/**
 * 运行指令
node tools/js-env-analyzer/generate-h5st-playwright.js `
  --cookie-file cookies.txt `
  --params '{"appid":"pc-item-soa","functionId":"pc_detailpage_wareBusiness","body":"{\"skuId\":\"10147072608797\",\"area\":\"19_1659_0_0\",\"num\":\"1\"}","client":"pc","clientVersion":"1.0.0"}'

 */
  /**
 * JD h5st generator — uses Playwright to call the real browser SDK.
 *
 * Usage:
 *   # Search API with cookie for authentication
 *   node tools/js-env-analyzer/generate-h5st-playwright.js \
 *     --cookie "pin=xxx; 3AB9D23F7A4B3C9B=xxx; __jda=xxx; __jdc=xxx" \
 *     --appid search-pc-java \
 *     --functionId pc_search_searchWare \
 *     --keyword "穿戴跳蛋" \
 *     --body '{"enc":"utf-8","s":23}'
 *
 *   # Detail API
 *   node tools/js-env-analyzer/generate-h5st-playwright.js \
 *     --cookie-file cookies.txt \
 *     --params '{"appid":"pc-item-soa","functionId":"pc_detailpage_wareBusiness","body":"{\"skuId\":\"123\"}"}'
 *
 *   # Without cookie (may trigger JD captcha)
 *   node tools/js-env-analyzer/generate-h5st-playwright.js --params '{"appid":"search-pc-java",...}'
 */

var fs = require('node:fs');
var path = require('node:path');

// ============================================================
// CLI helpers
// ============================================================
function readOption(args, name) {
  var index = args.indexOf(name);
  if (index === -1) return null;
  if (!args[index + 1]) throw new Error(name + ' requires a value');
  return args[index + 1];
}

function readParameters() {
  var args = process.argv.slice(2);
  var text = readOption(args, '--params');
  var inputPath = readOption(args, '--input');
  if (text && inputPath) throw new Error('Use only one of --params or --input');
  if (inputPath) text = fs.readFileSync(path.resolve(inputPath), 'utf8');
  if (!text && !process.stdin.isTTY) text = fs.readFileSync(0, 'utf8');
  if (!text) {
    var appid = readOption(args, '--appid') || 'search-pc-java';
    var functionId = readOption(args, '--functionId') || 'pc_search_searchWare';
    var body = readOption(args, '--body') || '{}';
    var keyword = readOption(args, '--keyword') || '';
    var uuid = readOption(args, '--uuid') || '';
    var loginType = readOption(args, '--loginType') || '3';
    var cthr = readOption(args, '--cthr') || '1';
    var p = { appid: appid, functionId: functionId, body: body, client: 'pc', clientVersion: '1.0.0', t: 0 };
    if (keyword) p.keyword = keyword;
    if (uuid) p.uuid = uuid;
    if (loginType) p.loginType = loginType;
    if (cthr) p.cthr = cthr;
    return p;
  }
  var parameters = JSON.parse(text);
  if (!parameters || Array.isArray(parameters) || typeof parameters !== 'object') {
    throw new Error('Signing parameters must be a JSON object');
  }
  return parameters;
}

function readCookie(args) {
  // --cookie "key=value; key2=value2"
  var raw = readOption(args, '--cookie');
  if (raw) return raw;

  // --cookie-file path/to/cookies.txt
  var filePath = readOption(args, '--cookie-file');
  if (filePath) {
    var resolved = path.resolve(filePath);
    if (!fs.existsSync(resolved)) throw new Error('Cookie file not found: ' + resolved);
    return fs.readFileSync(resolved, 'utf8').trim();
  }
  return null;
}

/**
 * Parse a Netscape-style cookie string into Playwright cookie objects.
 */
function parseCookies(cookieString) {
  if (!cookieString) return [];
  return cookieString.split(';').map(function (pair) {
    var eq = pair.indexOf('=');
    if (eq === -1) return null;
    return {
      name: pair.substring(0, eq).trim(),
      value: pair.substring(eq + 1).trim(),
      domain: '.jd.com',
      path: '/',
      httpOnly: false,
      secure: true,
      sameSite: 'Lax',
    };
  }).filter(Boolean);
}

// AppId mapping
var APPID_MAP = {
  'pc-item-soa': 'fb5df',
  'www-jd-com': 'b5216',
  'search-pc-java': 'f06cc',
};

// ============================================================
// Main
// ============================================================
async function main() {
  var args = process.argv.slice(2);
  var parameters = readParameters();
  var configAppId = parameters.appid || 'search-pc-java';
  var appId = APPID_MAP[configAppId] || 'f06cc';
  var cookieString = readCookie(args);

  // Lazy-load Playwright
  var playwright;
  try {
    playwright = require('playwright');
  } catch (e) {
    console.error('Playwright is not installed. Run: npm install playwright');
    process.exit(1);
  }

  var browser = await playwright.chromium.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled',
    ],
  });

  var context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
    viewport: { width: 1536, height: 864 },
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    geolocation: { latitude: 31.2304, longitude: 121.4737 },
    permissions: ['geolocation'],
  });

  // Set cookies if provided (before navigation)
  if (cookieString) {
    var cookies = parseCookies(cookieString);
    if (cookies.length > 0) {
      await context.addCookies(cookies);
      console.error('[cookie] ' + cookies.length + ' cookies set for .jd.com');
    }
  }

  // Extract x-api-eid-token from cookies (3AB9D23F7A4B3CSS)
  var extraEidToken = '';
  if (cookieString) {
    var cssMatch = cookieString.match(/3AB9D23F7A4B3CSS=([^;]+)/);
    if (cssMatch) extraEidToken = cssMatch[1];
  }

  // Inject real browser fingerprint (Canvas toDataURL + WebGL params)
  // Disabled: causes SDK compatibility issues. Use headless native fingerprint.
  // var initScriptPath = path.join(__dirname, 'real-fp-init.js');
  // if (fs.existsSync(initScriptPath)) {
  //   await context.addInitScript({ path: initScriptPath });
  //   console.error('[fp] Real browser fingerprint injected');
  // }

  var page = await context.newPage();

  // Navigate to a stable JD page (product detail loads SDK without redirects)
  console.error('[navigate] Loading JD page ...');
  await page.goto('https://item.jd.com/10147072608797.html', { waitUntil: 'networkidle', timeout: 60000 });

  // Wait for SDK to initialize
  console.error('[wait] Waiting for ParamsSign SDK ...');
  await page.waitForFunction(function () { return typeof window.ParamsSign === 'function'; }, { timeout: 15000 });
  console.error('[ready] SDK loaded');

  // Two-call approach: 1st triggers cactus fetch, 2nd uses cached token
  console.error('[sign] Phase 1: trigger cactus token fetch ...');
  await page.evaluate(async function (opts) {
    var signer = window.__jd_signer = new window.ParamsSign({ appId: opts.appId, beta: false });
    var params = Object.assign({}, opts.params, { t: Date.now() });
    await signer.sign(params); // triggers _$rgo() → cactus token fetch in background
  }, { params: parameters, appId: appId });

  // Wait for cactus XHR to complete
  console.error('[wait] Waiting for cactus token cache ...');
  await new Promise(function (r) { return setTimeout(r, 10000); });

  // Phase 2: sign again with cached token, then call API
  console.error('[sign] Phase 2: signing + calling API ...');
  var result = await page.evaluate(async function (opts) {
    var signer = window.__jd_signer || new window.ParamsSign({ appId: opts.appId, beta: false });
    var now = Date.now();
    var signParams = Object.assign({}, opts.params, { t: now });
    var signed = await signer.sign(signParams);

    // Build API URL and make request
    var urlStr = 'https://api.m.jd.com/api';
    var queryParts = [];
    var allParams = Object.assign({}, signParams, {
      h5st: signed.h5st,
      'x-api-eid-token': opts.xApiEidToken || ''
    });
    Object.keys(allParams).forEach(function (k) {
      if (allParams[k] !== undefined && allParams[k] !== null && k !== 'xApiEidToken') {
        queryParts.push(encodeURIComponent(k) + '=' + encodeURIComponent(typeof allParams[k] === 'object' ? JSON.stringify(allParams[k]) : String(allParams[k])));
      }
    });
    var apiUrl = urlStr + '?' + queryParts.join('&');

    var apiResp;
    try {
      var resp = await fetch(apiUrl, {
        headers: { 'Accept': 'application/json' },
        credentials: 'include'
      });
      var text = await resp.text();
      try { apiResp = JSON.parse(text); } catch (e) { apiResp = { _raw: text }; }
      apiResp._httpStatus = resp.status;
    } catch (e) {
      apiResp = { _error: e.message };
    }

    return {
      h5st: signed.h5st,
      _stk: signed._stk,
      t: now,
      apiResponse: apiResp,
    };
  }, { params: parameters, appId: appId, xApiEidToken: extraEidToken });

  await browser.close();

  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
}

main().catch(function (e) {
  console.error('Error:', e.message);
  process.exit(1);
});
