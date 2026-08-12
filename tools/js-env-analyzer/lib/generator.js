'use strict';

var catalog = require('./browser-catalog');

function quoted(value) {
  return JSON.stringify(String(value));
}

function propertyFromPath(path) {
  return path.slice(path.lastIndexOf('.') + 1);
}

function constructorFromPath(path) {
  return path.slice(0, path.indexOf('.prototype'));
}

function isFunctionMember(item) {
  return item.context === 'call' || /^(addEventListener|removeEventListener|dispatchEvent|postMessage|send|open|close|abort|readAs|setItem|getItem|removeItem|clear|getBoundingClientRect|createElement|querySelector|querySelectorAll|appendChild|removeChild|cloneNode|toDataURL)$/.test(propertyFromPath(item.path));
}

function stubExpression(property) {
  if (/^(crypto|msCrypto|chrome|screen)$/.test(property)) return '{}';
  if (/^(querySelectorAll|children|files)$/.test(property)) return '[]';
  if (/^(getBoundingClientRect)$/.test(property)) return '{}';
  if (/^(getItem)$/.test(property)) return 'null';
  if (/^(toDataURL|cookie|href|userAgent|language)$/.test(property)) return "''";
  return 'undefined';
}

function buildMapping(analysis) {
  var mapping = {};
  analysis.globals.forEach(function (item) {
    mapping[item.name] = {
      kind: item.kind,
      description: item.description,
      strategy: item.strategy,
      missingInRuntime: item.missingInRuntime,
      locations: item.locations
    };
  });
  analysis.prototypeMembers.forEach(function (item) {
    mapping[item.path] = {
      kind: 'prototype-member',
      description: 'Browser prototype member used by the target source',
      strategy: isFunctionMember(item) ? 'no-op function stub' : 'safe property descriptor',
      locations: item.locations
    };
  });
  return mapping;
}

function renderConstructor(name, lines) {
  lines.push("  if (typeof root[" + quoted(name) + "] === 'undefined') {");
  lines.push("    root[" + quoted(name) + "] = function " + name.replace(/[^A-Za-z0-9_$]/g, '') + "() {};");
  lines.push('  }');
}

function renderGlobal(item, lines) {
  var name = item.name;
  if (name === 'window') {
    lines.push("  if (typeof root.window === 'undefined') root.window = root;");
    return;
  }
  if (item.kind === 'constructor') {
    renderConstructor(name, lines);
    return;
  }
  if (item.kind === 'function') {
    lines.push("  if (typeof root[" + quoted(name) + "] === 'undefined') root[" + quoted(name) + "] = function () {");
    if (name === 'fetch') lines.push("    if (root.Promise && root.Promise.resolve) return root.Promise.resolve({ ok: true, status: 200, text: function () { return root.Promise.resolve(''); }, json: function () { return root.Promise.resolve({}); } });");
    else if (name === 'setTimeout' || name === 'setInterval') lines.push('    var callback = arguments[0]; if (typeof callback === \'function\') callback(); return 0;');
    else if (name === 'requestAnimationFrame') lines.push("    var callback = arguments[0]; if (typeof callback === 'function') callback(Date.now ? Date.now() : 0); return 0;");
    lines.push('  };');
    return;
  }
  if (name === 'console') {
    lines.push("  if (typeof root.console === 'undefined') root.console = {};");
    lines.push("  ['log', 'info', 'warn', 'error', 'debug'].forEach(function (method) { if (typeof root.console[method] !== 'function') root.console[method] = function () {}; });");
    return;
  }
  if (name === 'localStorage' || name === 'sessionStorage') {
    lines.push("  if (typeof root[" + quoted(name) + "] === 'undefined') root[" + quoted(name) + "] = (function () { var values = {}; return { getItem: function (key) { return Object.prototype.hasOwnProperty.call(values, key) ? values[key] : null; }, setItem: function (key, value) { values[key] = String(value); }, removeItem: function (key) { delete values[key]; }, clear: function () { values = {}; } }; }());");
    return;
  }
  if (name === 'document') {
    lines.push("  if (typeof root.document === 'undefined') root.document = { cookie: '', createElement: function () { return {}; }, querySelector: function () { return null; }, querySelectorAll: function () { return []; }, addEventListener: function () {}, removeEventListener: function () {} };");
    return;
  }
  if (name === 'navigator') {
    lines.push("  if (typeof root.navigator === 'undefined') root.navigator = { userAgent: '', language: '', platform: '', plugins: [] };");
    return;
  }
  if (name === 'location') {
    lines.push("  if (typeof root.location === 'undefined') root.location = { href: '', protocol: '', host: '', pathname: '', search: '', hash: '' };");
    return;
  }
  if (name === 'crypto') {
    lines.push("  if (typeof root.crypto === 'undefined') root.crypto = { getRandomValues: function (array) { return array; } };");
    return;
  }
  if (name === 'Reflect') {
    lines.push("  if (typeof root.Reflect === 'undefined') root.Reflect = {};");
    return;
  }
  lines.push("  if (typeof root[" + quoted(name) + "] === 'undefined') root[" + quoted(name) + '] = {};');
}

function renderPrototype(item, lines) {
  var constructor = constructorFromPath(item.path);
  var property = propertyFromPath(item.path);
  var instanceByPrototype = {
    Window: 'window',
    Document: 'document',
    Navigator: 'navigator',
    Location: 'location',
    Storage: 'localStorage'
  };
  var host = instanceByPrototype[constructor];
  renderConstructor(constructor, lines);
  if (host) {
    lines.push("  if (typeof root[" + quoted(host) + "] === 'undefined') root[" + quoted(host) + '] = {};');
    if (isFunctionMember(item)) {
      lines.push("  if (typeof root[" + quoted(host) + "][" + quoted(property) + "] === 'undefined') root[" + quoted(host) + "][" + quoted(property) + '] = function () { return ' + stubExpression(property) + '; };');
    } else {
      lines.push("  if (typeof root[" + quoted(host) + "][" + quoted(property) + "] === 'undefined') root[" + quoted(host) + "][" + quoted(property) + '] = ' + stubExpression(property) + ';');
    }
  }
  lines.push("  if (typeof root[" + quoted(constructor) + "].prototype[" + quoted(property) + "] === 'undefined') {");
  if (isFunctionMember(item)) {
    lines.push("    root[" + quoted(constructor) + "].prototype[" + quoted(property) + '] = function () { return ' + stubExpression(property) + '; };');
  } else {
    lines.push('    try { Object.defineProperty(root[' + quoted(constructor) + '].prototype, ' + quoted(property) + ', { configurable: true, enumerable: true, get: function () { return ' + stubExpression(property) + '; }, set: function () {} }); } catch (error) { root[' + quoted(constructor) + '].prototype[' + quoted(property) + '] = ' + stubExpression(property) + '; }');
  }
  lines.push('  }');
}

function renderShim(analysis) {
  var lines = [
    '(function (root) {',
    "  'use strict';",
    '  // Generated static compatibility shim. Native implementations are retained.',
    '  if (!root) return;'
  ];
  analysis.globals.forEach(function (item) { renderGlobal(item, lines); });
  analysis.prototypeMembers.forEach(function (item) { renderPrototype(item, lines); });
  lines.push("}(typeof globalThis !== 'undefined' ? globalThis : this));", '');
  return lines.join('\n');
}

function generateArtifacts(analysis) {
  return { shim: renderShim(analysis), mapping: buildMapping(analysis) };
}

module.exports = { buildMapping: buildMapping, generateArtifacts: generateArtifacts, renderShim: renderShim };
