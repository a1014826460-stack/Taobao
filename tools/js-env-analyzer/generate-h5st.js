'use strict';

// Loads the generated compatibility shim before the JD signing SDK.
var fs = require('node:fs');
var path = require('node:path');
var vm = require('node:vm');

var toolDirectory = __dirname;
var projectDirectory = path.resolve(toolDirectory, '..', '..');
var shimPath = path.join(toolDirectory, 'output', 'jd-security', 'browser-env-shim.js');
var targetPath = path.join(projectDirectory, 'tests', 'JD', 'js_security_v3_0.1.6.js');

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
  if (!text) return null;
  var parameters = JSON.parse(text);
  if (!parameters || Array.isArray(parameters) || typeof parameters !== 'object') {
    throw new Error('Signing parameters must be a JSON object');
  }
  return parameters;
}

if (!fs.existsSync(shimPath)) {
  throw new Error('Shim is missing. Run: node tools/js-env-analyzer/cli.js tests/JD/js_security_v3_0.1.6.js --out-dir tools/js-env-analyzer/output/jd-security');
}

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
  decodeURIComponent: decodeURIComponent
};
context.globalThis = context;
vm.createContext(context);
vm.runInContext(fs.readFileSync(shimPath, 'utf8'), context, { filename: shimPath });
vm.runInContext(fs.readFileSync(targetPath, 'utf8'), context, { filename: targetPath });

var signer = new context.window.ParamsSign({
  appId: 'fb5df',
  beta: false,
  onSign: function (event) {
    if (event.code !== 0) {
      process.stderr.write('JD signing error: ' + JSON.stringify(event) + '\n');
    }
  }
});

var exampleParameters = {
  functionId: 'pc_detail_wareBusiness',
  body: '{}',
  appid: 'pc-item-soa',
  client: 'pc',
  clientVersion: '1.0.0',
  t: Date.now()
};
var parameters = readParameters() || exampleParameters;
var signed = signer.signSync(parameters);

if (!signed || !signed.h5st) {
  throw new Error('h5st was not generated');
}

process.stdout.write(JSON.stringify({
  h5st: signed.h5st,
  _stk: signed._stk,
  _ste: signed._ste,
  params: signed
}, null, 2) + '\n');
