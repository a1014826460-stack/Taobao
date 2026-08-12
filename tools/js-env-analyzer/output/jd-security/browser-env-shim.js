(function (root) {
  'use strict';
  // Generated static compatibility shim. Native implementations are retained.
  if (!root) return;
  if (typeof root.window === 'undefined') root.window = root;
  if (typeof root.Reflect === 'undefined') root.Reflect = {};
  if (typeof root.document === 'undefined') root.document = { cookie: '', createElement: function () { return {}; }, querySelector: function () { return null; }, querySelectorAll: function () { return []; }, addEventListener: function () {}, removeEventListener: function () {} };
  if (typeof root.navigator === 'undefined') root.navigator = { userAgent: '', language: '', platform: '', plugins: [] };
  if (typeof root["setTimeout"] === 'undefined') root["setTimeout"] = function () {
    var callback = arguments[0]; if (typeof callback === 'function') callback(); return 0;
  };
  if (typeof root.console === 'undefined') root.console = {};
  ['log', 'info', 'warn', 'error', 'debug'].forEach(function (method) { if (typeof root.console[method] !== 'function') root.console[method] = function () {}; });
  if (typeof root["clearTimeout"] === 'undefined') root["clearTimeout"] = function () {
  };
  if (typeof root["Document"] === 'undefined') {
    root["Document"] = function Document() {};
  }
  if (typeof root["Element"] === 'undefined') {
    root["Element"] = function Element() {};
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root.location === 'undefined') root.location = { href: '', protocol: '', host: '', pathname: '', search: '', hash: '' };
  if (typeof root["Document"] === 'undefined') {
    root["Document"] = function Document() {};
  }
  if (typeof root["document"] === 'undefined') root["document"] = {};
  if (typeof root["document"]["all"] === 'undefined') root["document"]["all"] = undefined;
  if (typeof root["Document"].prototype["all"] === 'undefined') {
    try { Object.defineProperty(root["Document"].prototype, "all", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Document"].prototype["all"] = undefined; }
  }
  if (typeof root["Navigator"] === 'undefined') {
    root["Navigator"] = function Navigator() {};
  }
  if (typeof root["navigator"] === 'undefined') root["navigator"] = {};
  if (typeof root["navigator"]["userAgent"] === 'undefined') root["navigator"]["userAgent"] = '';
  if (typeof root["Navigator"].prototype["userAgent"] === 'undefined') {
    try { Object.defineProperty(root["Navigator"].prototype, "userAgent", { configurable: true, enumerable: true, get: function () { return ''; }, set: function () {} }); } catch (error) { root["Navigator"].prototype["userAgent"] = ''; }
  }
  if (typeof root["Document"] === 'undefined') {
    root["Document"] = function Document() {};
  }
  if (typeof root["document"] === 'undefined') root["document"] = {};
  if (typeof root["document"]["domain"] === 'undefined') root["document"]["domain"] = undefined;
  if (typeof root["Document"].prototype["domain"] === 'undefined') {
    try { Object.defineProperty(root["Document"].prototype, "domain", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Document"].prototype["domain"] = undefined; }
  }
  if (typeof root["Console"] === 'undefined') {
    root["Console"] = function Console() {};
  }
  if (typeof root["Console"].prototype["error"] === 'undefined') {
    root["Console"].prototype["error"] = function () { return undefined; };
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["crypto"] === 'undefined') root["window"]["crypto"] = {};
  if (typeof root["Window"].prototype["crypto"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "crypto", { configurable: true, enumerable: true, get: function () { return {}; }, set: function () {} }); } catch (error) { root["Window"].prototype["crypto"] = {}; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["msCrypto"] === 'undefined') root["window"]["msCrypto"] = {};
  if (typeof root["Window"].prototype["msCrypto"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "msCrypto", { configurable: true, enumerable: true, get: function () { return {}; }, set: function () {} }); } catch (error) { root["Window"].prototype["msCrypto"] = {}; }
  }
  if (typeof root["Document"] === 'undefined') {
    root["Document"] = function Document() {};
  }
  if (typeof root["document"] === 'undefined') root["document"] = {};
  if (typeof root["document"]["cookie"] === 'undefined') root["document"]["cookie"] = function () { return ''; };
  if (typeof root["Document"].prototype["cookie"] === 'undefined') {
    root["Document"].prototype["cookie"] = function () { return ''; };
  }
  if (typeof root["Console"] === 'undefined') {
    root["Console"] = function Console() {};
  }
  if (typeof root["Console"].prototype["log"] === 'undefined') {
    root["Console"].prototype["log"] = function () { return undefined; };
  }
  if (typeof root["Document"] === 'undefined') {
    root["Document"] = function Document() {};
  }
  if (typeof root["document"] === 'undefined') root["document"] = {};
  if (typeof root["document"]["createElement"] === 'undefined') root["document"]["createElement"] = function () { return undefined; };
  if (typeof root["Document"].prototype["createElement"] === 'undefined') {
    root["Document"].prototype["createElement"] = function () { return undefined; };
  }
  if (typeof root["Document"] === 'undefined') {
    root["Document"] = function Document() {};
  }
  if (typeof root["document"] === 'undefined') root["document"] = {};
  if (typeof root["document"]["getElementsByTagName"] === 'undefined') root["document"]["getElementsByTagName"] = function () { return undefined; };
  if (typeof root["Document"].prototype["getElementsByTagName"] === 'undefined') {
    root["Document"].prototype["getElementsByTagName"] = function () { return undefined; };
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["__JDWEBSIGNHELPER_$DATA__"] === 'undefined') root["window"]["__JDWEBSIGNHELPER_$DATA__"] = undefined;
  if (typeof root["Window"].prototype["__JDWEBSIGNHELPER_$DATA__"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "__JDWEBSIGNHELPER_$DATA__", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["__JDWEBSIGNHELPER_$DATA__"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["XMLHttpRequest"] === 'undefined') root["window"]["XMLHttpRequest"] = undefined;
  if (typeof root["Window"].prototype["XMLHttpRequest"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "XMLHttpRequest", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["XMLHttpRequest"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["__MICRO_APP_ENVIRONMENT_TEMPORARY__"] === 'undefined') root["window"]["__MICRO_APP_ENVIRONMENT_TEMPORARY__"] = undefined;
  if (typeof root["Window"].prototype["__MICRO_APP_ENVIRONMENT_TEMPORARY__"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "__MICRO_APP_ENVIRONMENT_TEMPORARY__", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["__MICRO_APP_ENVIRONMENT_TEMPORARY__"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["__MICRO_APP_ENVIRONMENT__"] === 'undefined') root["window"]["__MICRO_APP_ENVIRONMENT__"] = undefined;
  if (typeof root["Window"].prototype["__MICRO_APP_ENVIRONMENT__"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "__MICRO_APP_ENVIRONMENT__", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["__MICRO_APP_ENVIRONMENT__"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["rawWindow"] === 'undefined') root["window"]["rawWindow"] = undefined;
  if (typeof root["Window"].prototype["rawWindow"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "rawWindow", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["rawWindow"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["__MICRO_APP_PROXY_WINDOW__"] === 'undefined') root["window"]["__MICRO_APP_PROXY_WINDOW__"] = undefined;
  if (typeof root["Window"].prototype["__MICRO_APP_PROXY_WINDOW__"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "__MICRO_APP_PROXY_WINDOW__", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["__MICRO_APP_PROXY_WINDOW__"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["__MICRO_APP_BASE_APPLICATION__"] === 'undefined') root["window"]["__MICRO_APP_BASE_APPLICATION__"] = undefined;
  if (typeof root["Window"].prototype["__MICRO_APP_BASE_APPLICATION__"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "__MICRO_APP_BASE_APPLICATION__", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["__MICRO_APP_BASE_APPLICATION__"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["document"] === 'undefined') root["window"]["document"] = undefined;
  if (typeof root["Window"].prototype["document"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "document", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["document"] = undefined; }
  }
  if (typeof root["Document"] === 'undefined') {
    root["Document"] = function Document() {};
  }
  if (typeof root["document"] === 'undefined') root["document"] = {};
  if (typeof root["document"]["querySelector"] === 'undefined') root["document"]["querySelector"] = function () { return undefined; };
  if (typeof root["Document"].prototype["querySelector"] === 'undefined') {
    root["Document"].prototype["querySelector"] = function () { return undefined; };
  }
  if (typeof root["Element"] === 'undefined') {
    root["Element"] = function Element() {};
  }
  if (typeof root["Element"].prototype["scrollIntoViewIfNeeded"] === 'undefined') {
    try { Object.defineProperty(root["Element"].prototype, "scrollIntoViewIfNeeded", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Element"].prototype["scrollIntoViewIfNeeded"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["getComputedStyle"] === 'undefined') root["window"]["getComputedStyle"] = undefined;
  if (typeof root["Window"].prototype["getComputedStyle"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "getComputedStyle", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["getComputedStyle"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["localStorage"] === 'undefined') root["window"]["localStorage"] = undefined;
  if (typeof root["Window"].prototype["localStorage"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "localStorage", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["localStorage"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["navigator"] === 'undefined') root["window"]["navigator"] = undefined;
  if (typeof root["Window"].prototype["navigator"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "navigator", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["navigator"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["chrome"] === 'undefined') root["window"]["chrome"] = {};
  if (typeof root["Window"].prototype["chrome"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "chrome", { configurable: true, enumerable: true, get: function () { return {}; }, set: function () {} }); } catch (error) { root["Window"].prototype["chrome"] = {}; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["screen"] === 'undefined') root["window"]["screen"] = {};
  if (typeof root["Window"].prototype["screen"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "screen", { configurable: true, enumerable: true, get: function () { return {}; }, set: function () {} }); } catch (error) { root["Window"].prototype["screen"] = {}; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["outerWidth"] === 'undefined') root["window"]["outerWidth"] = undefined;
  if (typeof root["Window"].prototype["outerWidth"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "outerWidth", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["outerWidth"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["outerHeight"] === 'undefined') root["window"]["outerHeight"] = undefined;
  if (typeof root["Window"].prototype["outerHeight"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "outerHeight", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["outerHeight"] = undefined; }
  }
  if (typeof root["Location"] === 'undefined') {
    root["Location"] = function Location() {};
  }
  if (typeof root["location"] === 'undefined') root["location"] = {};
  if (typeof root["location"]["href"] === 'undefined') root["location"]["href"] = '';
  if (typeof root["Location"].prototype["href"] === 'undefined') {
    try { Object.defineProperty(root["Location"].prototype, "href", { configurable: true, enumerable: true, get: function () { return ''; }, set: function () {} }); } catch (error) { root["Location"].prototype["href"] = ''; }
  }
  if (typeof root["Location"] === 'undefined') {
    root["Location"] = function Location() {};
  }
  if (typeof root["location"] === 'undefined') root["location"] = {};
  if (typeof root["location"]["origin"] === 'undefined') root["location"]["origin"] = undefined;
  if (typeof root["Location"].prototype["origin"] === 'undefined') {
    try { Object.defineProperty(root["Location"].prototype, "origin", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Location"].prototype["origin"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["devicePixelRatio"] === 'undefined') root["window"]["devicePixelRatio"] = undefined;
  if (typeof root["Window"].prototype["devicePixelRatio"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "devicePixelRatio", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["devicePixelRatio"] = undefined; }
  }
  if (typeof root["Document"] === 'undefined') {
    root["Document"] = function Document() {};
  }
  if (typeof root["document"] === 'undefined') root["document"] = {};
  if (typeof root["document"]["referrer"] === 'undefined') root["document"]["referrer"] = undefined;
  if (typeof root["Document"].prototype["referrer"] === 'undefined') {
    try { Object.defineProperty(root["Document"].prototype, "referrer", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Document"].prototype["referrer"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["toString"] === 'undefined') root["window"]["toString"] = function () { return undefined; };
  if (typeof root["Window"].prototype["toString"] === 'undefined') {
    root["Window"].prototype["toString"] = function () { return undefined; };
  }
  if (typeof root["Navigator"] === 'undefined') {
    root["Navigator"] = function Navigator() {};
  }
  if (typeof root["navigator"] === 'undefined') root["navigator"] = {};
  if (typeof root["navigator"]["hardwareConcurrency"] === 'undefined') root["navigator"]["hardwareConcurrency"] = undefined;
  if (typeof root["Navigator"].prototype["hardwareConcurrency"] === 'undefined') {
    try { Object.defineProperty(root["Navigator"].prototype, "hardwareConcurrency", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Navigator"].prototype["hardwareConcurrency"] = undefined; }
  }
  if (typeof root["Window"] === 'undefined') {
    root["Window"] = function Window() {};
  }
  if (typeof root["window"] === 'undefined') root["window"] = {};
  if (typeof root["window"]["ParamsSign"] === 'undefined') root["window"]["ParamsSign"] = undefined;
  if (typeof root["Window"].prototype["ParamsSign"] === 'undefined') {
    try { Object.defineProperty(root["Window"].prototype, "ParamsSign", { configurable: true, enumerable: true, get: function () { return undefined; }, set: function () {} }); } catch (error) { root["Window"].prototype["ParamsSign"] = undefined; }
  }
}(typeof globalThis !== 'undefined' ? globalThis : this));
