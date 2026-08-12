'use strict';

var test = require('node:test');
var assert = require('node:assert/strict');
var childProcess = require('node:child_process');
var fs = require('node:fs');
var os = require('node:os');
var path = require('node:path');
var vm = require('node:vm');
var analyzer = require('../lib/analyzer');
var generator = require('../lib/generator');

test('reports unresolved browser globals with source positions', function () {
  var result = analyzer.analyzeSource(
    'window.location.href; navigator.userAgent;',
    'fixture.js'
  );

  assert.deepEqual(result.globals.map(function (item) {
    return item.name;
  }), ['window', 'navigator']);
  assert.deepEqual(result.globals[0].locations[0], { line: 1, column: 0 });
  assert.equal(typeof result.globals[0].missingInRuntime, 'boolean');
  assert.deepEqual(result.missingGlobals.map(function (item) { return item.name; }), ['window']);
});

test('renders an ES5 IIFE shim and mapping for detected dependencies', function () {
  var analysis = analyzer.analyzeSource('document.cookie; fetch("/");', 'generate.js');
  var artifacts = generator.generateArtifacts(analysis);

  assert.match(artifacts.shim, /^\(function \(root\) \{/);
  assert.equal(artifacts.mapping.document.strategy, 'minimal document object');
  assert.equal(artifacts.mapping['Document.prototype.cookie'].strategy, 'safe property descriptor');
  vm.runInNewContext(artifacts.shim, {});
});

test('adds inferred Window, Document, and Navigator members to host instances', function () {
  var analysis = analyzer.analyzeSource([
    'window.crypto.getRandomValues;',
    'document.getElementsByTagName("body");',
    'navigator.hardwareConcurrency;'
  ].join('\n'), 'host-members.js');
  var context = vm.createContext({});
  var artifacts = generator.generateArtifacts(analysis);

  assert.ok(analysis.prototypeMembers.some(function (item) {
    return item.path === 'Window.prototype.crypto';
  }));
  vm.runInContext(artifacts.shim, context);
  assert.equal(typeof vm.runInContext('window.crypto', context), 'object');
  assert.equal(typeof vm.runInContext('document.getElementsByTagName', context), 'function');
  assert.doesNotThrow(function () {
    vm.runInContext('navigator.hardwareConcurrency', context);
  });
});

test('excludes declarations while retaining unresolved catalog globals', function () {
  var source = 'var window = {}; function f(document) { return document.title; } fetch("/");';
  var result = analyzer.analyzeSource(source, 'scope.js');

  assert.deepEqual(result.globals.map(function (item) {
    return item.name;
  }), ['fetch']);
  assert.equal(result.globals[0].usage, 'call');
  assert.match(result.globals[0].description, /network/i);
});

test('detects direct and inferred browser prototype members', function () {
  var source = [
    'Element.prototype.getBoundingClientRect.call(node);',
    'document.cookie;',
    'window.postMessage({ ok: true }, "*");'
  ].join('\n');
  var result = analyzer.analyzeSource(source, 'prototype.js');

  assert.deepEqual(result.prototypeMembers.map(function (item) {
    return item.path;
  }), [
    'Element.prototype.getBoundingClientRect',
    'Document.prototype.cookie',
    'Window.prototype.postMessage'
  ]);
  assert.equal(result.prototypeMembers[0].context, 'call');
  assert.deepEqual(result.prototypeMembers[0].locations[0], { line: 1, column: 0 });
});

test('analyzes the JD security script and finds the sign method', function () {
  var target = path.resolve(__dirname, '../../../tests/JD/js_security_v3_0.1.6.js');
  var result = analyzer.analyzeFile(target);
  var source = fs.readFileSync(target, 'utf8');

  assert.match(source, /_\$PI\.prototype\.sign\s*=\s*function/);
  assert.ok(result.globals.length + result.prototypeMembers.length > 0);
});

test('CLI writes analysis, shim, and dependency map artifacts', function () {
  var target = path.resolve(__dirname, '../testdata/browser-dependencies.js');
  var outputDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'js-env-analyzer-'));
  var cli = path.resolve(__dirname, '../cli.js');

  childProcess.execFileSync(process.execPath, [cli, target, '--out-dir', outputDirectory], {
    encoding: 'utf8'
  });

  assert.equal(JSON.parse(fs.readFileSync(path.join(outputDirectory, 'analysis.json'), 'utf8')).file, target);
  assert.match(fs.readFileSync(path.join(outputDirectory, 'browser-env-shim.js'), 'utf8'), /^\(function \(root\) \{/);
  assert.equal(typeof JSON.parse(fs.readFileSync(path.join(outputDirectory, 'dependency-map.json'), 'utf8')), 'object');
  fs.rmSync(outputDirectory, { recursive: true, force: true });
});

test('h5st example script prints a signed payload', function () {
  var script = path.resolve(__dirname, '../generate-h5st.js');
  var output = childProcess.execFileSync(process.execPath, [script], {
    cwd: path.resolve(__dirname, '../../..'),
    encoding: 'utf8'
  });
  var result = JSON.parse(output);

  assert.equal(typeof result.h5st, 'string');
  assert.ok(result.h5st.length > 0);
  assert.equal(result.params.h5st, result.h5st);
});

test('h5st script signs JSON parameters received from standard input', function () {
  var script = path.resolve(__dirname, '../generate-h5st.js');
  var input = JSON.stringify({
    appid: 'search-pc-java',
    functionId: 'pc_search_searchWare',
    client: 'pc',
    clientVersion: '1.0.0',
    t: 1785233730002,
    body: 'e0e99439c054372f8c1459dfd7a6b57a5c4d949b8e392feb01437706fa21e415'
  });
  var output = childProcess.execFileSync(process.execPath, [script], {
    cwd: path.resolve(__dirname, '../../..'),
    input: input,
    encoding: 'utf8'
  });
  var result = JSON.parse(output);

  assert.equal(result.params.functionId, 'pc_search_searchWare');
  assert.equal(result.params.body, 'e0e99439c054372f8c1459dfd7a6b57a5c4d949b8e392feb01437706fa21e415');
  assert.equal(result.params.t, 1785233730002);
  assert.ok(result.h5st);
});
