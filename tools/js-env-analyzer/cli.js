#!/usr/bin/env node
'use strict';

var fs = require('node:fs');
var path = require('node:path');
var analyzer = require('./lib/analyzer');
var generator = require('./lib/generator');

function usage() {
  return 'Usage: node cli.js <target.js> [--out-dir <directory>]';
}

function readOption(args, name) {
  var index = args.indexOf(name);
  if (index === -1) return null;
  if (!args[index + 1]) throw new Error(name + ' requires a directory value');
  return args[index + 1];
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + '\n', 'utf8');
}

function main(args) {
  var target = args[0];
  if (!target || target === '--help' || target === '-h') {
    process.stdout.write(usage() + '\n');
    return target ? 0 : 1;
  }
  var resolvedTarget = path.resolve(target);
  if (!fs.existsSync(resolvedTarget) || !fs.statSync(resolvedTarget).isFile()) {
    throw new Error('Target JavaScript file was not found: ' + resolvedTarget);
  }
  var outDir = path.resolve(readOption(args, '--out-dir') || process.cwd());
  var analysis = analyzer.analyzeFile(resolvedTarget);
  var artifacts = generator.generateArtifacts(analysis);
  fs.mkdirSync(outDir, { recursive: true });
  var outputs = {
    analysis: path.join(outDir, 'analysis.json'),
    shim: path.join(outDir, 'browser-env-shim.js'),
    mapping: path.join(outDir, 'dependency-map.json')
  };
  writeJson(outputs.analysis, analysis);
  fs.writeFileSync(outputs.shim, artifacts.shim, 'utf8');
  writeJson(outputs.mapping, artifacts.mapping);
  Object.keys(outputs).forEach(function (key) { process.stdout.write(outputs[key] + '\n'); });
  return 0;
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (error) {
  process.stderr.write('js-env-analyzer: ' + error.message + '\n');
  process.exitCode = 1;
}
