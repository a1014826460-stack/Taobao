# JavaScript Browser Environment Analyzer

This standalone Node.js utility statically scans a JavaScript file for browser-host globals and browser prototype members that a non-browser runtime may lack. It then writes a dependency report, an ES5 IIFE compatibility shim, and a dependency-to-stub mapping.

## Install and Run

```powershell
npm --prefix tools/js-env-analyzer install
node tools/js-env-analyzer/cli.js tests/JD/js_security_v3_0.1.6.js --out-dir tools/js-env-analyzer/output/jd-security
```

Output files:

- `analysis.json`: detected browser globals and prototype members, with line/column positions, inferred use context, a short source summary, and `missingInRuntime` based on the Node.js process that runs the tool.
- `browser-env-shim.js`: an ES5 IIFE that keeps native definitions and adds only missing globals, methods, and safe property descriptors.
- `dependency-map.json`: `missing item -> simulation strategy` entries with source locations.

Inject `browser-env-shim.js` before evaluating the target in a browser-external runtime. The generated shim is intentionally minimal: it avoids `TypeError` for identified access paths but does not reproduce DOM, network, fingerprinting, or cryptographic behavior.

## Scope

The analyzer parses source with Acorn and tracks declarations in program, function, block, catch, and parameter scopes. It reports unresolved identifiers only when they match the catalog of browser APIs. It also recognizes `Constructor.prototype.member`, `Object.getPrototypeOf(host).member`, and catalog-backed host members such as `document.cookie`.

Computed property names that cannot be statically resolved are not reported as specific prototype members. Dynamic runtime-only dependencies are outside this static scan's coverage.

## JD Sign-Method Case

The included tests analyze `tests/JD/js_security_v3_0.1.6.js` and assert that its asynchronous encryption wrapper is present:

```js
_$PI.prototype.sign = function (_$Pd) {
  return _$GF.resolve(this.signSync(_$Pd));
};
```

Run all tests with:

```powershell
npm --prefix tools/js-env-analyzer test
```

## Passing H5ST Parameters

`generate-h5st.js` accepts a JSON object from standard input, `--input <file>`, or `--params '<json>'`. The object must contain the exact request values; do not change its `body` serialization or `t` after signing.

```powershell
@'
{"appid":"search-pc-java","functionId":"pc_search_searchWare","client":"pc","clientVersion":"1.0.0","t":1785233730002,"body":"e0e99439c054372f8c1459dfd7a6b57a5c4d949b8e392feb01437706fa21e415"}
'@ | node tools/js-env-analyzer/generate-h5st.js
```
