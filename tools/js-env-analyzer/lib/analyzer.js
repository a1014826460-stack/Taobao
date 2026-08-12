'use strict';

var fs = require('node:fs');
var acorn = require('acorn');
var catalog = require('./browser-catalog');

function Scope(parent, type) {
  this.parent = parent;
  this.type = type;
  this.bindings = Object.create(null);
}

function addPattern(pattern, scope) {
  if (!pattern) return;
  if (pattern.type === 'Identifier') scope.bindings[pattern.name] = true;
  else if (pattern.type === 'RestElement') addPattern(pattern.argument, scope);
  else if (pattern.type === 'AssignmentPattern') addPattern(pattern.left, scope);
  else if (pattern.type === 'ArrayPattern') pattern.elements.forEach(function (item) { addPattern(item, scope); });
  else if (pattern.type === 'ObjectPattern') pattern.properties.forEach(function (property) { addPattern(property.value || property.argument, scope); });
}

function isNode(value) {
  return value && typeof value.type === 'string';
}

function eachChild(node, callback) {
  Object.keys(node).forEach(function (key) {
    if (key === 'loc' || key === 'start' || key === 'end') return;
    var value = node[key];
    if (isNode(value)) callback(value, key);
    else if (Array.isArray(value)) value.forEach(function (item) { if (isNode(item)) callback(item, key); });
  });
}

function nearestVarScope(scope) {
  while (scope.parent && scope.type === 'block') scope = scope.parent;
  return scope;
}

function createScopes(node, parent, current, scopes) {
  var scope = current;
  if (node.type === 'Program') {
    scope = new Scope(null, 'program');
    scopes.set(node, scope);
  } else if (/Function/.test(node.type) || node.type === 'ArrowFunctionExpression') {
    scope = new Scope(current, 'function');
    scopes.set(node, scope);
    if (node.id) addPattern(node.id, scope);
    node.params.forEach(function (param) { addPattern(param, scope); });
  } else if (node.type === 'BlockStatement' || node.type === 'CatchClause') {
    scope = new Scope(current, 'block');
    scopes.set(node, scope);
    if (node.type === 'CatchClause') addPattern(node.param, scope);
  }

  if (node.type === 'FunctionDeclaration' && node.id) addPattern(node.id, current);
  if (node.type === 'ClassDeclaration' && node.id) addPattern(node.id, current);
  if (node.type === 'VariableDeclaration') {
    node.declarations.forEach(function (declaration) {
      addPattern(declaration.id, node.kind === 'var' ? nearestVarScope(current) : current);
    });
  }
  eachChild(node, function (child) { createScopes(child, node, scope, scopes); });
}

function declared(scope, name) {
  for (var cursor = scope; cursor; cursor = cursor.parent) {
    if (cursor.bindings[name]) return true;
  }
  return false;
}

function loc(node) {
  return { line: node.loc.start.line, column: node.loc.start.column };
}

function propertyName(member) {
  if (!member.computed && member.property.type === 'Identifier') return member.property.name;
  if (member.computed && member.property.type === 'Literal' && typeof member.property.value === 'string') return member.property.value;
  return null;
}

function expressionName(node) {
  return node && node.type === 'Identifier' ? node.name : null;
}

function prototypePath(member) {
  var property = propertyName(member);
  var object = member.object;
  var constructor;
  if (!property || property === 'prototype') return null;
  if (object.type === 'MemberExpression' && propertyName(object) === 'prototype') {
    constructor = expressionName(object.object);
    if (constructor && catalog.HOST_TO_PROTOTYPE[constructor]) return catalog.HOST_TO_PROTOTYPE[constructor] + '.prototype.' + property;
  }
  if (object.type === 'CallExpression' && object.callee.type === 'MemberExpression' &&
      expressionName(object.callee.object) === 'Object' && propertyName(object.callee) === 'getPrototypeOf' && object.arguments.length) {
    constructor = expressionName(object.arguments[0]);
    if (constructor && catalog.HOST_TO_PROTOTYPE[constructor]) return catalog.HOST_TO_PROTOTYPE[constructor] + '.prototype.' + property;
  }
  constructor = expressionName(object);
  if (constructor && catalog.HOST_TO_PROTOTYPE[constructor]) return catalog.HOST_TO_PROTOTYPE[constructor] + '.prototype.' + property;
  if (object.type === 'MemberExpression') {
    var rootName = expressionName(object.object);
    var rootProperty = propertyName(object);
    if (rootName && rootProperty && catalog.HOST_TO_PROTOTYPE[rootName]) {
      return catalog.HOST_TO_PROTOTYPE[rootName] + '.prototype.' + rootProperty;
    }
  }
  return null;
}

function usageFor(node, parent) {
  if (!parent) return 'read';
  if (parent.type === 'CallExpression' && parent.callee === node) return 'call';
  if (parent.type === 'NewExpression' && parent.callee === node) return 'construct';
  if (parent.type === 'MemberExpression' && parent.object === node) return 'member-access';
  return 'read';
}

function memberContext(node, parent) {
  if (parent && parent.type === 'CallExpression' && parent.callee === node) return 'call';
  if (parent && parent.type === 'MemberExpression' && parent.object === node &&
      (propertyName(parent) === 'call' || propertyName(parent) === 'apply' || propertyName(parent) === 'bind')) return 'call';
  if (parent && parent.type === 'AssignmentExpression' && parent.left === node) return 'write';
  return 'read';
}

function codeSummary(source, node) {
  return source.slice(node.start, Math.min(node.end + 100, source.length)).split(/[\r\n]/)[0];
}

function rootHas(name) {
  try {
    return typeof globalThis !== 'undefined' && name in globalThis;
  } catch (error) {
    return false;
  }
}

function record(map, key, data) {
  if (!map[key]) map[key] = data;
  map[key].locations.push(data.location);
}

function isReferenceIdentifier(node, parent, key) {
  if (!parent) return false;
  if ((parent.type === 'VariableDeclarator' && key === 'id') ||
      ((/Function/.test(parent.type) || parent.type === 'ClassDeclaration' || parent.type === 'ClassExpression') && (key === 'id' || key === 'params')) ||
      (parent.type === 'MemberExpression' && key === 'property' && !parent.computed) ||
      (parent.type === 'Property' && key === 'key' && !parent.computed) ||
      (parent.type === 'MethodDefinition' && key === 'key' && !parent.computed) ||
      (parent.type === 'LabeledStatement' && key === 'label') ||
      (parent.type === 'BreakStatement' && key === 'label') ||
      (parent.type === 'ContinueStatement' && key === 'label')) return false;
  return true;
}

function analyzeSource(source, filePath) {
  var ast = acorn.parse(source, { ecmaVersion: 'latest', sourceType: 'script', locations: true, allowHashBang: true });
  var scopes = new Map();
  createScopes(ast, null, null, scopes);
  var globals = Object.create(null);
  var prototypes = Object.create(null);

  function visit(node, scope, parent, key) {
    var nextScope = scopes.get(node) || scope;
    if (node.type === 'Identifier' && isReferenceIdentifier(node, parent, key) && catalog.HOST_GLOBALS[node.name] && !declared(scope, node.name)) {
      var info = catalog.HOST_GLOBALS[node.name];
      record(globals, node.name, {
        name: node.name, kind: info.kind, usage: usageFor(node, parent), description: info.description,
        strategy: info.strategy, missingInRuntime: !rootHas(node.name), locations: [loc(node)], location: loc(node)
      });
    }
    if (node.type === 'MemberExpression') {
      var path = prototypePath(node);
      if (path) {
        record(prototypes, path, {
          path: path, context: memberContext(node, parent), summary: codeSummary(source, node),
          locations: [loc(node)], location: loc(node)
        });
      }
    }
    eachChild(node, function (child, childKey) { visit(child, nextScope, node, childKey); });
  }
  visit(ast, scopes.get(ast), null, null);
  function clean(items) {
    return Object.keys(items).sort(function (a, b) { return items[a].locations[0].line - items[b].locations[0].line || items[a].locations[0].column - items[b].locations[0].column; }).map(function (key) {
      delete items[key].location;
      return items[key];
    });
  }
  var globalItems = clean(globals);
  return {
    file: filePath || '<source>',
    globals: globalItems,
    missingGlobals: globalItems.filter(function (item) { return item.missingInRuntime; }),
    prototypeMembers: clean(prototypes)
  };
}

function analyzeFile(filePath) {
  return analyzeSource(fs.readFileSync(filePath, 'utf8'), filePath);
}

module.exports = { analyzeSource: analyzeSource, analyzeFile: analyzeFile };
