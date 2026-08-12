'use strict';

var HOST_GLOBALS = {
  window: { description: 'browser global object', strategy: 'alias global object', kind: 'object', prototype: 'Window' },
  document: { description: 'DOM document access', strategy: 'minimal document object', kind: 'object', prototype: 'Document' },
  navigator: { description: 'browser and device metadata', strategy: 'minimal navigator object', kind: 'object', prototype: 'Navigator' },
  location: { description: 'browser URL location', strategy: 'minimal location object', kind: 'object', prototype: 'Location' },
  localStorage: { description: 'persistent key-value storage', strategy: 'in-memory storage stub', kind: 'object', prototype: 'Storage' },
  sessionStorage: { description: 'session key-value storage', strategy: 'in-memory storage stub', kind: 'object', prototype: 'Storage' },
  fetch: { description: 'network request API', strategy: 'Promise-returning stub', kind: 'function' },
  XMLHttpRequest: { description: 'HTTP request constructor', strategy: 'minimal XMLHttpRequest constructor', kind: 'constructor', prototype: 'XMLHttpRequest' },
  crypto: { description: 'Web Crypto API', strategy: 'minimal crypto object', kind: 'object', prototype: 'Crypto' },
  console: { description: 'browser developer console', strategy: 'no-op console methods', kind: 'object', prototype: 'Console' },
  setTimeout: { description: 'timer scheduling API', strategy: 'synchronous timer stub', kind: 'function' },
  clearTimeout: { description: 'timer cancellation API', strategy: 'no-op timer cancellation', kind: 'function' },
  setInterval: { description: 'repeating timer scheduling API', strategy: 'synchronous timer stub', kind: 'function' },
  clearInterval: { description: 'repeating timer cancellation API', strategy: 'no-op timer cancellation', kind: 'function' },
  requestAnimationFrame: { description: 'animation frame scheduling API', strategy: 'synchronous callback stub', kind: 'function' },
  cancelAnimationFrame: { description: 'animation frame cancellation API', strategy: 'no-op animation cancellation', kind: 'function' },
  WebSocket: { description: 'web socket constructor', strategy: 'minimal WebSocket constructor', kind: 'constructor', prototype: 'WebSocket' },
  Worker: { description: 'web worker constructor', strategy: 'minimal Worker constructor', kind: 'constructor', prototype: 'Worker' },
  Blob: { description: 'binary blob constructor', strategy: 'minimal Blob constructor', kind: 'constructor', prototype: 'Blob' },
  FileReader: { description: 'file reader constructor', strategy: 'minimal FileReader constructor', kind: 'constructor', prototype: 'FileReader' },
  URL: { description: 'URL parser constructor', strategy: 'minimal URL constructor', kind: 'constructor', prototype: 'URL' },
  Element: { description: 'DOM element constructor', strategy: 'minimal Element constructor', kind: 'constructor', prototype: 'Element' },
  HTMLElement: { description: 'HTML element constructor', strategy: 'minimal HTMLElement constructor', kind: 'constructor', prototype: 'HTMLElement' },
  Document: { description: 'DOM document constructor', strategy: 'minimal Document constructor', kind: 'constructor', prototype: 'Document' },
  Window: { description: 'browser window constructor', strategy: 'minimal Window constructor', kind: 'constructor', prototype: 'Window' },
  Navigator: { description: 'browser navigator constructor', strategy: 'minimal Navigator constructor', kind: 'constructor', prototype: 'Navigator' },
  Location: { description: 'browser location constructor', strategy: 'minimal Location constructor', kind: 'constructor', prototype: 'Location' },
  Storage: { description: 'browser storage constructor', strategy: 'in-memory Storage constructor', kind: 'constructor', prototype: 'Storage' },
  Promise: { description: 'promise constructor', strategy: 'native Promise when available', kind: 'constructor' },
  Proxy: { description: 'proxy constructor', strategy: 'native Proxy when available', kind: 'constructor' },
  Reflect: { description: 'reflection API', strategy: 'minimal reflection object', kind: 'object' }
};

var HOST_TO_PROTOTYPE = {};
Object.keys(HOST_GLOBALS).forEach(function (name) {
  if (HOST_GLOBALS[name].prototype) {
    HOST_TO_PROTOTYPE[name] = HOST_GLOBALS[name].prototype;
  }
});

module.exports = {
  HOST_GLOBALS: HOST_GLOBALS,
  HOST_TO_PROTOTYPE: HOST_TO_PROTOTYPE
};
