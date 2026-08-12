'use strict';

/**
 * JD h5st generator with FULL browser environment.
 *
 * Uses browser-env-full.js — a comprehensive shim that provides real
 * values for document, window, navigator, screen, canvas (2D + WebGL),
 * XMLHttpRequest, crypto, and all prototype chains that the JD SDK needs.
 *
 * Usage:
 *   node tools/js-env-analyzer/generate-h5st-real.js --appid pc-item-soa --functionId pc_detailpage_wareBusiness --body '{"skuId":"123"}'
 *   node tools/js-env-analyzer/generate-h5st-real.js --params '{"appid":"pc-item-soa","functionId":"...","body":"...","t":...}'
 *   node tools/js-env-analyzer/generate-h5st-real.js --input params.json
 */

var fs = require('node:fs');
var path = require('node:path');
var vm = require('node:vm');

var toolDirectory = __dirname;
var projectDirectory = path.resolve(toolDirectory, '..', '..');

// Paths
var fullEnvPath = path.join(toolDirectory, 'output', 'jd-security', 'browser-env-full.js');
// Use v0.1.8 SDK (newer, better compatibility with cactus token server)
var sdkPath = path.join(toolDirectory, 'js_security_v3_0.1.8_clean.js');
if (!fs.existsSync(sdkPath)) {
  // Fallback to v0.1.6
  sdkPath = path.join(projectDirectory, 'tests', 'JD', 'js_security_v3_0.1.6.js');
}

// ============================================================
// Timestamp fix
// The JD SDK's obfuscated date formatter uses a literal "yyyy"
// placeholder in the VM.  Patch Array.join to replace it.
// ============================================================
function applyTimestampFix(context) {
  var origJoin = context.Array.prototype.join;
  context.Array.prototype.join = function (sep) {
    var result = origJoin.apply(this, arguments);
    if (sep === ';' && typeof result === 'string' && result.length > 50) {
      var year = String(new context.Date().getFullYear());
      result = result.replace(/(^|;)yyyy(?=\d{13}(;|$))/g, function (match, prefix) {
        return prefix + year;
      });
    }
    return result;
  };
}

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
    // Build from individual flags
    var appid = readOption(args, '--appid') || 'pc-item-soa';
    var functionId = readOption(args, '--functionId') || 'pc_detailpage_wareBusiness';
    var body = readOption(args, '--body') || '{}';
    return { appid: appid, functionId: functionId, body: body, client: 'pc', clientVersion: '1.0.0', t: Date.now() };
  }
  var parameters = JSON.parse(text);
  if (!parameters || Array.isArray(parameters) || typeof parameters !== 'object') {
    throw new Error('Signing parameters must be a JSON object');
  }
  // Always ensure t is set to current time
  if (!parameters.t) parameters.t = Date.now();
  return parameters;
}

// AppId mapping (URL appid → SDK appId)
// Search API and detail API use DIFFERENT appIds and _stk signatures.
var APPID_MAP = {
  'pc-item-soa': 'fb5df',       // detail page wareBusiness
  'www-jd-com': 'b5216',        // homepage
  'search-pc-java': 'f06cc',    // search
};

// ============================================================
// Verify prerequisites
// ============================================================
if (!fs.existsSync(fullEnvPath)) {
  throw new Error(
    'Full environment shim not found: ' + fullEnvPath + '\n' +
    'Run: node tools/js-env-analyzer/cli.js tests/JD/js_security_v3_0.1.6.js --out-dir tools/js-env-analyzer/output/jd-security\n' +
    'Then copy browser-env-full.js to the same directory.'
  );
}
if (!fs.existsSync(sdkPath)) {
  throw new Error('JD SDK not found: ' + sdkPath);
}

// ============================================================
// Build VM context with native objects
// ============================================================
var context = {
  console: console,
  Promise: Promise,
  Date: Date,
  JSON: JSON,
  Math: Math,
  Object: Object,
  Array: Array,
  String: String,
  Number: Number,
  Boolean: Boolean,
  RegExp: RegExp,
  Error: Error,
  TypeError: TypeError,
  parseInt: parseInt,
  isNaN: isNaN,
  encodeURIComponent: encodeURIComponent,
  decodeURIComponent: decodeURIComponent,
  setTimeout: setTimeout,
  clearTimeout: clearTimeout,
  setInterval: setInterval,
  clearInterval: clearInterval,
  require: require,
  Buffer: Buffer,
};
context.globalThis = context;
vm.createContext(context);

// Apply timestamp fix BEFORE loading so it catches all join() calls
applyTimestampFix(context);

// Deterministic Math.random for stable fingerprint
var _mathSeed = 12345;
var origRandom = context.Math.random;
context.Math.random = function() {
  _mathSeed = (_mathSeed * 1103515245 + 12345) & 0x7fffffff;
  return _mathSeed / 0x7fffffff;
};

// ============================================================
// Load full browser environment
// ============================================================
vm.runInContext(fs.readFileSync(fullEnvPath, 'utf8'), context, { filename: 'browser-env-full.js' });

// ============================================================
// Inject real browser fingerprint data (Canvas toDataURL)
// ============================================================
var realFpPatchPath = path.join(toolDirectory, 'output', 'jd-security', 'real-fingerprint-patch.js');
if (fs.existsSync(realFpPatchPath)) {
  vm.runInContext(fs.readFileSync(realFpPatchPath, 'utf8'), context, { filename: 'real-fingerprint-patch.js' });
}

// ============================================================
// Load JD security SDK
// ============================================================
vm.runInContext(fs.readFileSync(sdkPath, 'utf8'), context, { filename: 'js_security_sdk.js' });

// v0.1.8 exports ParamsSignMain instead of assigning to window.ParamsSign
if (typeof context.ParamsSignMain === 'function' && typeof context.window.ParamsSign === 'undefined') {
  context.window.ParamsSign = context.ParamsSignMain;
}

// ============================================================
// Generate h5st (two-phase: trigger token fetch → wait → sign with cache)
// ============================================================
var cliArgs = process.argv.slice(2);
var parameters = readParameters();
var configAppId = readOption(cliArgs, '--appid') || parameters.appid || 'pc-item-soa';
var appId = APPID_MAP[configAppId] || 'fb5df';

var signer = new context.window.ParamsSign({
  appId: appId,
  beta: false,
  onSign: function (event) {
    if (event.code !== 0) {
      process.stderr.write('JD signing error: ' + JSON.stringify(event) + '\n');
    }
  }
});

// Phase 1: trigger fingerprint computation and async token fetch
var firstSigned = signer.signSync(parameters);
if (!firstSigned || !firstSigned.h5st) {
  throw new Error('h5st was not generated — check the SDK and environment');
}

// Phase 2: wait for token cache, then sign again with cached tk03w token
// The SDK schedules _$rgo() via setTimeout after the first signSync.
// We wait 8 seconds for the XHR to cactus.jd.com to complete.
setTimeout(function () {
  var finalParams = readParameters(); // re-read params
  finalParams.t = Date.now(); // always use fresh timestamp
  var signed = signer.signSync(finalParams);

  if (!signed || !signed.h5st) {
    throw new Error('Second h5st generation failed');
  }

  process.stdout.write(JSON.stringify({
    h5st: signed.h5st,
    _stk: signed._stk,
    _ste: signed._ste,
    params: signed,
    environment: 'browser-env-full (Chrome 150 / Win10 fingerprint)',
    note: 'Two-phase: first call triggers cactus token fetch, second uses cached tk03w'
  }, null, 2) + '\n');
}, 8000);
