# JavaScript Browser Environment Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Node.js tool that statically identifies browser-environment dependencies in a JavaScript source file and generates an ES5 IIFE environment shim plus a JSON dependency map.

**Architecture:** `lib/analyzer.js` will parse source with Acorn, maintain lexical scopes while walking the AST, collect unresolved browser-global references, and recognize direct and indirect browser prototype accesses. `lib/generator.js` will convert normalized findings to an ES5-compatible IIFE shim and mapping data. `cli.js` will provide the command-line interface and write both artifacts. Node's built-in `node:test` runner will test fixture-level detection, generation safety, and the provided JD security script's `_$PI.prototype.sign` case.

**Tech Stack:** Node.js CommonJS, `acorn`, `acorn-walk`, `node:test`, `node:assert/strict`.

---

## File Structure

- Create: `tools/js-env-analyzer/package.json` - isolated tool metadata, dependencies, scripts, and CommonJS configuration.
- Create: `tools/js-env-analyzer/lib/browser-catalog.js` - browser host globals, constructors, common members, descriptions, and stub-return strategies.
- Create: `tools/js-env-analyzer/lib/analyzer.js` - AST parse, lexical scope tracking, unresolved reference collection, prototype-member detection, and public `analyzeSource` / `analyzeFile` APIs.
- Create: `tools/js-env-analyzer/lib/generator.js` - safe ES5 IIFE shim rendering and dependency mapping construction.
- Create: `tools/js-env-analyzer/cli.js` - argument parsing and artifact writing.
- Create: `tools/js-env-analyzer/README.md` - installation, command usage, output formats, limits, and JD sign-case example.
- Create: `tools/js-env-analyzer/test/analyzer.test.js` - unit and integration tests with temporary fixtures and the provided target file.
- Create: `tools/js-env-analyzer/test/fixtures/browser-dependencies.js` - deterministic browser-global and prototype dependency fixture.

### Task 1: Establish isolated Node tool and test harness

**Files:**
- Create: `tools/js-env-analyzer/package.json`
- Create: `tools/js-env-analyzer/test/fixtures/browser-dependencies.js`
- Create: `tools/js-env-analyzer/test/analyzer.test.js`

- [ ] **Step 1: Write the failing package/API smoke test**

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const { analyzeSource } = require('../../lib/analyzer');

test('reports unresolved browser globals with source positions', function () {
  const result = analyzeSource('window.location.href; navigator.userAgent;', 'fixture.js');
  assert.deepEqual(result.globals.map(function (item) { return item.name; }), ['window', 'navigator']);
  assert.deepEqual(result.globals[0].locations[0], { line: 1, column: 0 });
});
```

- [ ] **Step 2: Run the focused test and verify it fails because the analyzer is absent**

Run: `npm --prefix tools/js-env-analyzer test -- --test-name-pattern="unresolved browser globals"`

Expected: failure with `Cannot find module '../../lib/analyzer'`.

- [ ] **Step 3: Add package metadata and a minimal analyzer export**

```json
{
  "name": "js-env-analyzer",
  "private": true,
  "version": "1.0.0",
  "type": "commonjs",
  "scripts": { "test": "node --test" },
  "dependencies": { "acorn": "^8.15.0", "acorn-walk": "^8.3.4" }
}
```

```js
function analyzeSource() {
  return { globals: [], prototypeMembers: [] };
}
module.exports = { analyzeSource: analyzeSource };
```

- [ ] **Step 4: Install dependencies and run the test to confirm the expected assertion failure**

Run: `npm --prefix tools/js-env-analyzer install; npm --prefix tools/js-env-analyzer test -- --test-name-pattern="unresolved browser globals"`

Expected: the module loads but the assertion fails because no globals are collected.

- [ ] **Step 5: Commit the test harness**

```powershell
git add tools/js-env-analyzer/package.json tools/js-env-analyzer/package-lock.json tools/js-env-analyzer/test
git commit -m "test: establish js environment analyzer harness"
```

### Task 2: Implement AST scope-aware browser global analysis

**Files:**
- Create: `tools/js-env-analyzer/lib/browser-catalog.js`
- Modify: `tools/js-env-analyzer/lib/analyzer.js`
- Modify: `tools/js-env-analyzer/test/analyzer.test.js`

- [ ] **Step 1: Write failing lexical-scope and global catalog tests**

```js
test('excludes declarations while retaining unresolved catalog globals', function () {
  const source = 'var window = {}; function f(document) { return document.title; } fetch("/");';
  const result = analyzeSource(source, 'scope.js');
  assert.deepEqual(result.globals.map(function (item) { return item.name; }), ['fetch']);
  assert.equal(result.globals[0].usage, 'call');
  assert.match(result.globals[0].description, /network/i);
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `npm --prefix tools/js-env-analyzer test -- --test-name-pattern="excludes declarations"`

Expected: failure because declarations and nested parameter scopes are not handled.

- [ ] **Step 3: Implement catalog metadata and a scope-aware identifier walker**

```js
const HOST_GLOBALS = {
  window: { description: 'browser global object', strategy: 'alias global object' },
  document: { description: 'DOM document access', strategy: 'minimal document object' },
  fetch: { description: 'network request API', strategy: 'Promise-returning stub' }
};

function locationOf(node) {
  return { line: node.loc.start.line, column: node.loc.start.column };
}
```

Implement declaration registration for `var`, `let`, `const`, function names/parameters, class names, catch parameters, and import bindings. Treat identifier occurrences in declaration/property-key/label positions as non-references. For each unresolved identifier present in `HOST_GLOBALS`, aggregate source locations, infer `call`, `construct`, `member-access`, or `read` from its parent node, and attach the catalog description and strategy.

- [ ] **Step 4: Run all analyzer tests and verify they pass**

Run: `npm --prefix tools/js-env-analyzer test`

Expected: all current tests pass.

- [ ] **Step 5: Commit AST global analysis**

```powershell
git add tools/js-env-analyzer/lib tools/js-env-analyzer/test/analyzer.test.js
git commit -m "feat: detect unresolved browser globals from AST"
```

### Task 3: Detect browser prototype dependencies and contextual member use

**Files:**
- Modify: `tools/js-env-analyzer/lib/browser-catalog.js`
- Modify: `tools/js-env-analyzer/lib/analyzer.js`
- Modify: `tools/js-env-analyzer/test/fixtures/browser-dependencies.js`
- Modify: `tools/js-env-analyzer/test/analyzer.test.js`

- [ ] **Step 1: Write failing prototype detection tests**

```js
test('detects direct and inferred browser prototype members', function () {
  const source = [
    'Element.prototype.getBoundingClientRect.call(node);',
    'document.cookie;',
    'window.postMessage({ ok: true }, "*");'
  ].join('\n');
  const result = analyzeSource(source, 'prototype.js');
  assert.deepEqual(result.prototypeMembers.map(function (item) { return item.path; }), [
    'Element.prototype.getBoundingClientRect',
    'Document.prototype.cookie',
    'Window.prototype.postMessage'
  ]);
  assert.equal(result.prototypeMembers[0].context, 'call');
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `npm --prefix tools/js-env-analyzer test -- --test-name-pattern="direct and inferred browser prototype members"`

Expected: failure because prototype members are not reported.

- [ ] **Step 3: Implement prototype path resolution and normalized result records**

```js
function prototypePathForMember(member, globals) {
  // Recognize Constructor.prototype.member and host aliases such as document.cookie.
  // Return null for computed properties without a static string key.
}
```

Cover `Document`, `Element`, `HTMLElement`, `Window`, `Navigator`, `Location`, `Storage`, `XMLHttpRequest`, `WebSocket`, `Worker`, `Blob`, `FileReader`, and `URL`; recognize direct `Constructor.prototype.member`, `Object.getPrototypeOf(host).member`, and catalog-defined host-instance members (for example `document.cookie` maps to `Document.prototype.cookie`). Store `path`, `location`, `context` (`call`, `write`, or `read`), and a short code excerpt as `summary`. Deduplicate paths while retaining all locations.

- [ ] **Step 4: Run all Node tests and verify they pass**

Run: `npm --prefix tools/js-env-analyzer test`

Expected: all tests pass, including the new prototype checks.

- [ ] **Step 5: Commit prototype analysis**

```powershell
git add tools/js-env-analyzer/lib tools/js-env-analyzer/test
git commit -m "feat: report browser prototype dependencies"
```

### Task 4: Generate ES5 IIFE shims and JSON dependency mappings

**Files:**
- Create: `tools/js-env-analyzer/lib/generator.js`
- Modify: `tools/js-env-analyzer/test/analyzer.test.js`

- [ ] **Step 1: Write failing generation and execution-safety tests**

```js
const vm = require('node:vm');
const { generateArtifacts } = require('../../lib/generator');

test('renders an ES5 IIFE shim and mapping for detected dependencies', function () {
  const analysis = analyzeSource('document.cookie; fetch("/");', 'generate.js');
  const artifacts = generateArtifacts(analysis);
  assert.match(artifacts.shim, /^\(function \(root\) \{/);
  assert.equal(artifacts.mapping.document.strategy, 'minimal document object');
  assert.equal(artifacts.mapping['Document.prototype.cookie'].strategy, 'safe property descriptor');
  vm.runInNewContext(artifacts.shim, {});
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `npm --prefix tools/js-env-analyzer test -- --test-name-pattern="renders an ES5 IIFE shim"`

Expected: failure with `Cannot find module '../../lib/generator'`.

- [ ] **Step 3: Implement deterministic ES5-safe renderer**

```js
function generateArtifacts(analysis) {
  return {
    shim: renderShim(analysis),
    mapping: buildMapping(analysis)
  };
}
```

Render only `var`, function expressions, string concatenation, conditional checks, and an IIFE `(function (root) { ... }(typeof globalThis !== 'undefined' ? globalThis : this));`. Use guarded definitions so native APIs are preserved. Generate correct return strategies: `{}` for objects, `''` for text-style getters, `[]` for collection methods, `Promise.resolve(...)` where `Promise` exists for async APIs, and no-op functions for event/message methods. Define prototype stubs using `Object.defineProperty` only when safely available, with assignment fallback. Build mapping entries as `{ kind, description, strategy, locations }`.

- [ ] **Step 4: Run all Node tests and verify they pass**

Run: `npm --prefix tools/js-env-analyzer test`

Expected: all tests pass and the generated IIFE executes in a clean VM context.

- [ ] **Step 5: Commit artifact generation**

```powershell
git add tools/js-env-analyzer/lib/generator.js tools/js-env-analyzer/test/analyzer.test.js
git commit -m "feat: generate ES5 browser environment shims"
```

### Task 5: Add CLI, JD `sign` case, documentation, and end-to-end verification

**Files:**
- Create: `tools/js-env-analyzer/cli.js`
- Create: `tools/js-env-analyzer/README.md`
- Modify: `tools/js-env-analyzer/package.json`
- Modify: `tools/js-env-analyzer/test/analyzer.test.js`

- [ ] **Step 1: Write failing JD sign-case and CLI output tests**

```js
test('analyzes the JD security script and finds the sign method', function () {
  const target = path.resolve(__dirname, '../../../tests/JD/js_security_v3_0.1.6.js');
  const result = analyzeFile(target);
  const source = fs.readFileSync(target, 'utf8');
  assert.match(source, /_\$PI\.prototype\.sign\s*=\s*function/);
  assert.ok(result.globals.length + result.prototypeMembers.length > 0);
});
```

Use `child_process.execFileSync(process.execPath, ['cli.js', target, '--out-dir', outputDir])`, then assert that `analysis.json` parses, `browser-env-shim.js` starts with the IIFE, and `dependency-map.json` is an object.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `npm --prefix tools/js-env-analyzer test -- --test-name-pattern="JD security script|CLI output"`

Expected: failure because no CLI or `analyzeFile` API exists.

- [ ] **Step 3: Implement CLI and public file analysis API**

```js
#!/usr/bin/env node
var args = process.argv.slice(2);
var target = args[0];
var outDir = readOption(args, '--out-dir') || process.cwd();
var analysis = analyzer.analyzeFile(target);
var artifacts = generator.generateArtifacts(analysis);
writeJson(path.join(outDir, 'analysis.json'), analysis);
writeText(path.join(outDir, 'browser-env-shim.js'), artifacts.shim);
writeJson(path.join(outDir, 'dependency-map.json'), artifacts.mapping);
```

Validate the input path, create the output directory recursively, write UTF-8 artifacts, and print each output path. Add `"bin": { "js-env-analyzer": "cli.js" }` and `"analyze": "node cli.js"` to `package.json`.

- [ ] **Step 4: Document installation and all output artifacts**

Include this executable example in `tools/js-env-analyzer/README.md`:

```powershell
npm --prefix tools/js-env-analyzer install
node tools/js-env-analyzer/cli.js tests/JD/js_security_v3_0.1.6.js --out-dir tools/js-env-analyzer/output/jd-security
```

Document static-analysis limits: generated shims make discovered accesses safe but do not reproduce cryptographic, DOM, network, or fingerprint semantics; unknown computed member names are intentionally reported only at their resolvable base API.

- [ ] **Step 5: Run the complete test suite and JD CLI end-to-end command**

Run: `npm --prefix tools/js-env-analyzer test; Remove-Item -Recurse -Force tools/js-env-analyzer/output/jd-security -ErrorAction SilentlyContinue; node tools/js-env-analyzer/cli.js tests/JD/js_security_v3_0.1.6.js --out-dir tools/js-env-analyzer/output/jd-security; Get-Item tools/js-env-analyzer/output/jd-security/analysis.json,tools/js-env-analyzer/output/jd-security/browser-env-shim.js,tools/js-env-analyzer/output/jd-security/dependency-map.json`

Expected: test exit code 0; CLI exits 0 and writes three non-empty artifacts. Inspect the JSON to confirm globals include only browser-catalog items used by the target and locations are 1-based line/0-based column coordinates.

- [ ] **Step 6: Commit the complete tool**

```powershell
git add tools/js-env-analyzer
git commit -m "feat: add browser environment dependency analyzer"
```
