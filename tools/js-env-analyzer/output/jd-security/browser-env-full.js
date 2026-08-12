'use strict';

/**
 * browser-env-full.js — Comprehensive browser environment shim for JD h5st SDK.
 *
 * Provides REAL browser values for all APIs that the JD js_security_v3 SDK
 * accesses, including Canvas 2D, WebGL, DOM, navigator, screen, etc.
 *
 * Usage: Inject this BEFORE loading the JD SDK in a Node.js VM context.
 */

(function (root) {
  if (!root || root.__JD_FULL_ENV_LOADED) return;
  root.__JD_FULL_ENV_LOADED = true;

  // ============================================================
  // Real browser values (captured from Chrome 150 / Win10)
  // ============================================================
  var REAL = {
    ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    platform: "Win32",
    language: "zh-CN",
    languages: ["zh-CN", "zh"],
    hardwareConcurrency: 12,
    deviceMemory: 32,
    maxTouchPoints: 10,
    vendor: "Google Inc.",
    productSub: "20030107",

    screenW: 1536, screenH: 864, screenAvailW: 1536, screenAvailH: 824,
    colorDepth: 24, pixelDepth: 24,
    innerW: 1036, innerH: 655, outerW: 1051, outerH: 806,
    devicePixelRatio: 1.25,

    webglVendor: "WebKit",
    webglRenderer: "WebKit WebGL",
    webglVersion: "WebGL 1.0 (OpenGL ES 2.0 Chromium)",
    webglSLVersion: "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
    webglMaxTexture: 16384,
    webglMaxRenderbuffer: 16384,
    webglMaxCombined: 32,

    cookie: "__jdv=76161171|direct|-|none|-|1785407536360; __jdu=17854075363601606079882; areaId=19; PCSYCityID=CN_440000_440100_0; shshshfpa=5590a6bb-a972-3e34-079a-6e265d4e4d0f-1785407537; shshshfpx=5590a6bb-a972-3e34-079a-6e265d4e4d0f-1785407537; TrackID=1yVpSKzWzEWR_FzycyRhasAiKo_UYDqr7IqqxLoWMVAVqCkWEydAhMKakGIWqhles-Hxpn9V9WOnHLPcG9-4pIm5f3c_nhxRaKTMtUcx_lAI; pinId=bq4bwXOjKE0ruHbdbqreNg; pin=jd_cElDNImwyPUF; unick=9cp3o4w1o2simi; ceshi3.com=000; _tp=%2FlDSPiH4yxXGVi4SH%2BxgaQ%3D%3D; wlfstk_smdl=5cy25arynf41k3pp6qd72lg1higxo54t; mail_times=4%2C1%2C1785407727411; umc_count=1; ipLoc-djd=19-1659-37264-37360; cn=0; 3AB9D23F7A4B3CSS=jdd03CTCYZZNZ77QGRZJDXO3BUYCJRCPB6XGTKJ7C4EWIVTCX4EE3FZIGTU7YYMN3BKPLIPP6DWUYMWG6FGADTVENFRKQCMAAAAM7WOKDUAYAAAAACE4C566BRCA4NUX; __jda=143920055.17854075363601606079882.1785407536.1785418183.1785423677.3; __jdc=143920055; __jdb=143920055.5.17854075363601606079882|3.1785423677; 3AB9D23F7A4B3C9B=CTCYZZNZ77QGRZJDXO3BUYCJRCPB6XGTKJ7C4EWIVTCX4EE3FZIGTU7YYMN3BKPLIPP6DWUYMWG6FGADTVENFRKQCM; token=1c9ea7215b0c380c9817d3821c9e1b85,3,991902; sdtoken=AAbEsBpEIOVjqTAKCQtvQu17DUNxCAEVFgBXkHXYruH8SEH6cW9vHBfKp6xWGrEl35506xVirreLgL9TkQaa1aBlYMeGpgq7NkvUELvx-NpAETldsCBgarlHoNQFcP16mPhU0Zxcl3aF-hUk0HnxV6WIwGPxqa3i_UN4; shshshfpb=BApXWy8adsPpAZgirWzXQgLVTB1HmiPzVBscBchho9xJ1PdZfQoXznj7FpSbtKrZGVeQQvavnsaw2IupjvaVYt9MvOgm2_gidJbY; cid=9; o2State=; is_avif=onAVIF",
    domain: "jd.com",
    referrer: "",
    locationHref: "https://item.jd.com/10147072608797.html",
    locationOrigin: "https://item.jd.com",
    timezone: "Etc/GMT-8",
    timezoneOffset: -480,
  };

  // ============================================================
  // Helpers
  // ============================================================
  function def(obj, name, value) {
    Object.defineProperty(obj, name, {
      value: value, writable: true, enumerable: true, configurable: true
    });
  }

  function defGet(obj, name, getter) {
    Object.defineProperty(obj, name, {
      get: getter, enumerable: true, configurable: true
    });
  }

  // ============================================================
  // 1. Location
  // ============================================================
  function buildLocation() {
    var loc = {};
    defGet(loc, 'href', function () { return REAL.locationHref; });
    defGet(loc, 'protocol', function () { return 'https:'; });
    defGet(loc, 'host', function () { return 'item.jd.com'; });
    defGet(loc, 'hostname', function () { return 'item.jd.com'; });
    defGet(loc, 'port', function () { return ''; });
    defGet(loc, 'pathname', function () { return '/10147072608797.html'; });
    defGet(loc, 'search', function () { return ''; });
    defGet(loc, 'hash', function () { return ''; });
    defGet(loc, 'origin', function () { return REAL.locationOrigin; });
    loc.toString = function () { return REAL.locationHref; };
    return loc;
  }

  // ============================================================
  // 2. Navigator
  // ============================================================
  function buildNavigator() {
    var nav = {};
    defGet(nav, 'userAgent', function () { return REAL.ua; });
    def(nav, 'platform', REAL.platform);
    def(nav, 'language', REAL.language);
    def(nav, 'languages', REAL.languages);
    def(nav, 'hardwareConcurrency', REAL.hardwareConcurrency);
    def(nav, 'deviceMemory', REAL.deviceMemory);
    def(nav, 'maxTouchPoints', REAL.maxTouchPoints);
    def(nav, 'vendor', REAL.vendor);
    def(nav, 'vendorSub', '');
    def(nav, 'productSub', REAL.productSub);
    def(nav, 'cookieEnabled', true);
    def(nav, 'doNotTrack', null);
    def(nav, 'onLine', true);

    // Plugins array
    var pluginNames = ["PDF Viewer", "Chrome PDF Viewer", "Chromium PDF Viewer", "Microsoft Edge PDF Viewer", "WebKit built-in PDF"];
    var plugins = [];
    for (var i = 0; i < pluginNames.length; i++) {
      var p = {
        name: pluginNames[i],
        description: "Portable Document Format",
        filename: "internal-pdf-viewer",
        length: 2,
        item: function (idx) { return this[idx]; },
        namedItem: function (name) { for (var j = 0; j < pluginNames.length; j++) { if (pluginNames[j] === name) return plugins[j]; } return null; },
        refresh: function () {}
      };
      plugins.push(p);
    }
    plugins.item = function (i) { return plugins[i]; };
    plugins.namedItem = function (n) { for (var j = 0; j < plugins.length; j++) { if (plugins[j].name === n) return plugins[j]; } return null; };
    plugins.refresh = function () {};
    def(nav, 'plugins', plugins);

    // MimeTypes
    var mimeTypes = [
      { type: "application/pdf", description: "Portable Document Format", suffixes: "pdf" },
      { type: "text/pdf", description: "Portable Document Format", suffixes: "pdf" }
    ];
    mimeTypes.item = function (i) { return mimeTypes[i]; };
    mimeTypes.namedItem = function (n) { for (var j = 0; j < mimeTypes.length; j++) { if (mimeTypes[j].type === n) return mimeTypes[j]; } return null; };
    def(nav, 'mimeTypes', mimeTypes);

    nav.javaEnabled = function () { return false; };
    nav.taintEnabled = function () { return false; };

    return nav;
  }

  // ============================================================
  // 3. Screen
  // ============================================================
  function buildScreen() {
    var scr = {};
    def(scr, 'width', REAL.screenW);
    def(scr, 'height', REAL.screenH);
    def(scr, 'availWidth', REAL.screenAvailW);
    def(scr, 'availHeight', REAL.screenAvailH);
    def(scr, 'colorDepth', REAL.colorDepth);
    def(scr, 'pixelDepth', REAL.pixelDepth);
    def(scr, 'availTop', 0);
    def(scr, 'availLeft', 0);
    return scr;
  }

  // ============================================================
  // 4. Storage (localStorage / sessionStorage)
  // ============================================================
  function buildStorage() {
    var data = {};
    return {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(data, k) ? data[k] : null; },
      setItem: function (k, v) { data[k] = String(v); },
      removeItem: function (k) { delete data[k]; },
      clear: function () { data = {}; },
      get length() { return Object.keys(data).length; },
      key: function (i) { return Object.keys(data)[i] || null; }
    };
  }

  // ============================================================
  // 5. Canvas 2D Context (with deterministic pixel rendering)
  // ============================================================
  function buildCanvas2DContext(canvas) {
    var state = {
      fillStyle: '#000000',
      strokeStyle: '#000000',
      font: '10px sans-serif',
      textBaseline: 'alphabetic',
      textAlign: 'start',
      globalAlpha: 1,
      lineWidth: 1,
      transform: [1, 0, 0, 1, 0, 0],
      imageData: null
    };

    var ctx = {
      // Canvas back-reference
      canvas: canvas,

      // Style properties
      get fillStyle() { return state.fillStyle; },
      set fillStyle(v) { state.fillStyle = v; },
      get strokeStyle() { return state.strokeStyle; },
      set strokeStyle(v) { state.strokeStyle = v; },
      get font() { return state.font; },
      set font(v) { state.font = v; },
      get textBaseline() { return state.textBaseline; },
      set textBaseline(v) { state.textBaseline = v; },
      get textAlign() { return state.textAlign; },
      set textAlign(v) { state.textAlign = v; },
      get globalAlpha() { return state.globalAlpha; },
      set globalAlpha(v) { state.globalAlpha = v; },
      get lineWidth() { return state.lineWidth; },
      set lineWidth(v) { state.lineWidth = v; },

      // Drawing methods
      fillRect: function () {},
      strokeRect: function () {},
      clearRect: function () {},
      fillText: function () {},
      strokeText: function () {},
      measureText: function (text) {
        return {
          width: text.length * 7.2,
          actualBoundingBoxAscent: 10,
          actualBoundingBoxDescent: 3,
          actualBoundingBoxLeft: 0,
          actualBoundingBoxRight: text.length * 7.2,
          fontBoundingBoxAscent: 12,
          fontBoundingBoxDescent: 3
        };
      },
      beginPath: function () {},
      closePath: function () {},
      moveTo: function () {},
      lineTo: function () {},
      bezierCurveTo: function () {},
      quadraticCurveTo: function () {},
      arc: function () {},
      arcTo: function () {},
      ellipse: function () {},
      rect: function () {},
      fill: function () {},
      stroke: function () {},
      clip: function () {},

      // Transform
      save: function () {},
      restore: function () {},
      scale: function () {},
      rotate: function () {},
      translate: function () {},
      transform: function () {},
      setTransform: function () {},
      resetTransform: function () {},

      // Gradients & Patterns
      createLinearGradient: function () { return { addColorStop: function () {} }; },
      createRadialGradient: function () { return { addColorStop: function () {} }; },
      createConicGradient: function () { return { addColorStop: function () {} }; },
      createPattern: function () { return {}; },

      // Image data
      createImageData: function (w, h) {
        var arr = new Uint8ClampedArray((w || 1) * (h || 1) * 4);
        return { width: w || 1, height: h || 1, data: arr };
      },
      getImageData: function (x, y, w, h) {
        // Return deterministic pixel data based on dimensions
        var len = w * h * 4;
        var arr = new Uint8ClampedArray(len);
        for (var i = 0; i < len; i += 4) {
          var px = ((i / 4) % w) + x;
          var py = Math.floor((i / 4) / w) + y;
          arr[i] = (px * 17) % 256;       // R
          arr[i + 1] = (py * 31) % 256;   // G
          arr[i + 2] = ((px + py) * 13) % 256; // B
          arr[i + 3] = 255;               // A
        }
        return { width: w, height: h, data: arr };
      },
      putImageData: function () {},

      // Pixel data export — deterministic per canvas dimensions
      toDataURL: function (type, quality) {
        // Generate a deterministic "canvas fingerprint" based on canvas dimensions
        var seed = (canvas.width || 300) * 65536 + (canvas.height || 150);
        var b64 = '';
        var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
        for (var i = 0; i < 256; i++) {
          seed = (seed * 1103515245 + 12345) & 0x7fffffff;
          b64 += chars[seed % 64];
        }
        return 'data:image/png;base64,' + b64;
      },
      toBlob: function (callback, type, quality) {
        if (typeof callback === 'function') callback(null);
      },

      // Text
      getLineDash: function () { return []; },
      setLineDash: function () {},

      drawImage: function () {},
      drawFocusIfNeeded: function () {},

      // Compositing
      globalCompositeOperation: 'source-over',
      imageSmoothingEnabled: true,
      imageSmoothingQuality: 'low',

      // Shadows
      shadowBlur: 0, shadowColor: 'rgba(0,0,0,0)',
      shadowOffsetX: 0, shadowOffsetY: 0,

      // Line styles
      lineCap: 'butt', lineJoin: 'miter',
      miterLimit: 10,
      getLineDash: function () { return []; },
      setLineDash: function () {},
      lineDashOffset: 0,

      // Other standard canvas props
      isPointInPath: function () { return false; },
      isPointInStroke: function () { return false; },
      scrollPathIntoView: function () {},
    };

    return ctx;
  }

  // ============================================================
  // 6. WebGL Context (with real GPU parameters)
  // ============================================================
  function buildWebGLContext() {
    var params = {};
    params[0x1F00] = REAL.webglVendor;    // VENDOR
    params[0x1F01] = REAL.webglRenderer;  // RENDERER
    params[0x1F02] = REAL.webglVersion;   // VERSION
    params[0x8B8C] = REAL.webglSLVersion; // SHADING_LANGUAGE_VERSION
    params[0x0D33] = REAL.webglMaxTexture; // MAX_TEXTURE_SIZE
    params[0x0D3A] = new Int32Array([32767, 32767]); // MAX_VIEWPORT_DIMS
    params[0x84E8] = REAL.webglMaxRenderbuffer; // MAX_RENDERBUFFER_SIZE
    params[0x8B4D] = REAL.webglMaxCombined; // MAX_COMBINED_TEXTURE_IMAGE_UNITS
    params[0x8869] = 16;   // MAX_VERTEX_ATTRIBS
    params[0x8B4C] = 16;   // MAX_TEXTURE_IMAGE_UNITS
    params[0x8B4B] = 32;   // MAX_VARYING_VECTORS
    params[0x8DFB] = 34921; // MAX_VERTEX_UNIFORM_VECTORS
    params[0x8DFC] = 34921; // MAX_FRAGMENT_UNIFORM_VECTORS
    params[0x0D35] = 3379;  // RED_BITS
    params[0x0D36] = 3379;  // GREEN_BITS
    params[0x0D37] = 3379;  // BLUE_BITS
    params[0x0D38] = 3379;  // ALPHA_BITS
    params[0x0D39] = 3379;  // DEPTH_BITS
    params[0x0D3B] = 3379;  // STENCIL_BITS
    params[0x9240] = false; // UNPACK_FLIP_Y_WEBGL

    var extensions = [
      "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_clip_control",
      "EXT_color_buffer_half_float", "EXT_depth_clamp", "EXT_disjoint_timer_query",
      "EXT_float_blend", "EXT_frag_depth", "EXT_polygon_offset_clamp",
      "EXT_shader_texture_lod", "EXT_texture_compression_bptc",
      "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic",
      "EXT_texture_mirror_clamp_to_edge", "EXT_sRGB",
      "KHR_parallel_shader_compile", "OES_element_index_uint",
      "OES_fbo_render_mipmap", "OES_standard_derivatives",
      "OES_texture_float", "OES_texture_float_linear",
      "OES_texture_half_float", "OES_texture_half_float_linear",
      "OES_vertex_array_object", "WEBGL_blend_func_extended",
      "WEBGL_color_buffer_float", "WEBGL_compressed_texture_s3tc",
      "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info",
      "WEBGL_debug_shaders", "WEBGL_depth_texture",
      "WEBGL_draw_buffers", "WEBGL_lose_context",
      "WEBGL_multi_draw", "WEBGL_polygon_mode"
    ];

    var bufferId = 0;

    return {
      VENDOR: REAL.webglVendor,
      RENDERER: REAL.webglRenderer,
      VERSION: REAL.webglVersion,
      SHADING_LANGUAGE_VERSION: REAL.webglSLVersion,
      MAX_TEXTURE_SIZE: REAL.webglMaxTexture,
      MAX_RENDERBUFFER_SIZE: REAL.webglMaxRenderbuffer,
      MAX_COMBINED_TEXTURE_IMAGE_UNITS: REAL.webglMaxCombined,
      MAX_VIEWPORT_DIMS: new Int32Array([32767, 32767]),

      getParameter: function (p) { return params[p] !== undefined ? params[p] : null; },
      getSupportedExtensions: function () { return extensions.slice(); },
      getExtension: function (name) { return extensions.indexOf(name) >= 0 ? {} : null; },

      // Shader / Program
      createShader: function (type) { return { _id: ++bufferId, _type: type }; },
      shaderSource: function () {},
      compileShader: function () {},
      getShaderParameter: function (shader, p) { return p === 0x8B81 || p === 0x8B80 ? true : false; },
      getShaderInfoLog: function () { return ''; },
      deleteShader: function () {},
      createProgram: function () { return { _id: ++bufferId }; },
      attachShader: function () {},
      detachShader: function () {},
      linkProgram: function () {},
      getProgramParameter: function (prog, p) { return p === 0x8B82 || p === 0x8B80 ? true : false; },
      getProgramInfoLog: function () { return ''; },
      useProgram: function () {},
      deleteProgram: function () {},
      validateProgram: function () {},

      // Buffers
      createBuffer: function () { return { _id: ++bufferId }; },
      bindBuffer: function () {},
      bufferData: function () {},
      bufferSubData: function () {},
      deleteBuffer: function () {},

      // Attributes
      getAttribLocation: function (prog, name) { return 0; },
      enableVertexAttribArray: function () {},
      disableVertexAttribArray: function () {},
      vertexAttribPointer: function () {},
      getActiveAttrib: function () { return null; },
      getActiveUniform: function () { return null; },

      // Textures
      createTexture: function () { return { _id: ++bufferId }; },
      bindTexture: function () {},
      texImage2D: function () {},
      texParameteri: function () {},
      activeTexture: function () {},
      generateMipmap: function () {},
      deleteTexture: function () {},

      // Framebuffers
      createFramebuffer: function () { return { _id: ++bufferId }; },
      bindFramebuffer: function () {},
      framebufferTexture2D: function () {},
      deleteFramebuffer: function () {},
      createRenderbuffer: function () { return { _id: ++bufferId }; },
      bindRenderbuffer: function () {},
      renderbufferStorage: function () {},
      framebufferRenderbuffer: function () {},
      deleteRenderbuffer: function () {},

      // Drawing
      drawArrays: function () {},
      drawElements: function () {},
      clear: function () {},
      clearColor: function () {},
      clearDepth: function () {},
      clearStencil: function () {},
      viewport: function () {},
      scissor: function () {},

      // State
      enable: function () {},
      disable: function () {},
      blendFunc: function () {},
      depthFunc: function () {},
      colorMask: function () {},
      depthMask: function () {},
      stencilMask: function () {},
      frontFace: function () {},
      cullFace: function () {},
      lineWidth: function () {},
      polygonOffset: function () {},

      // Uniform
      getUniformLocation: function (prog, name) { return { _name: name }; },
      uniform1i: function () {},
      uniform1f: function () {},
      uniform2f: function () {},
      uniform3f: function () {},
      uniform4f: function () {},
      uniformMatrix4fv: function () {},

      // Errors
      getError: function () { return 0; },
      NO_ERROR: 0,

      // Misc
      flush: function () {},
      finish: function () {},
      readPixels: function () { return new Uint8Array(4); },

      // Constants
      ARRAY_BUFFER: 0x8892,
      ELEMENT_ARRAY_BUFFER: 0x8893,
      STATIC_DRAW: 0x88E4,
      DYNAMIC_DRAW: 0x88E8,
      TRIANGLES: 0x0004,
      TRIANGLE_STRIP: 0x0005,
      FRAGMENT_SHADER: 0x8B30,
      VERTEX_SHADER: 0x8B31,
      COMPILE_STATUS: 0x8B81,
      LINK_STATUS: 0x8B82,
      TEXTURE_2D: 0x0DE1,
      TEXTURE0: 0x84C0,
      RGBA: 0x1908,
      UNSIGNED_BYTE: 0x1401,
      DEPTH_TEST: 0x0B71,
      BLEND: 0x0BE2,
      COLOR_BUFFER_BIT: 0x4000,
      DEPTH_BUFFER_BIT: 0x0100,
      STENCIL_BUFFER_BIT: 0x0400,
    };
  }

  // ============================================================
  // 7. Document
  // ============================================================
  function buildDocument() {
    var doc = {};

    def(doc, 'cookie', REAL.cookie);
    defGet(doc, 'domain', function () { return REAL.domain; });
    def(doc, 'referrer', REAL.referrer);
    def(doc, 'all', undefined);
    def(doc, 'title', '');
    def(doc, 'characterSet', 'UTF-8');
    def(doc, 'contentType', 'text/html');
    def(doc, 'hidden', false);
    def(doc, 'visibilityState', 'visible');
    def(doc, 'readyState', 'complete');
    def(doc, 'doctype', { name: 'html' });
    def(doc, 'documentElement', { style: {}, getAttribute: function () { return null; } });
    def(doc, 'body', { style: {}, appendChild: function () { return {}; } });
    def(doc, 'head', { style: {}, appendChild: function () { return {}; } });
    def(doc, 'styleSheets', []);
    def(doc, 'images', []);
    def(doc, 'forms', []);
    def(doc, 'links', []);

    // Event methods
    doc.addEventListener = function () {};
    doc.removeEventListener = function () {};
    doc.dispatchEvent = function () { return true; };

    // createElement — the most critical method
    doc.createElement = function (tagName) {
      var tag = (tagName || '').toLowerCase();
      var el = {
        tagName: tag.toUpperCase(),
        nodeType: 1,
        style: {},
        children: [],
        childNodes: [],
        attributes: {},
        innerHTML: '',
        innerText: '',
        textContent: '',

        setAttribute: function (name, value) { this.attributes[name] = value; },
        getAttribute: function (name) { return this.attributes[name] || null; },
        removeAttribute: function (name) { delete this.attributes[name]; },
        appendChild: function (child) { this.children.push(child); return child; },
        removeChild: function (child) { var i = this.children.indexOf(child); if (i >= 0) this.children.splice(i, 1); return child; },
        addEventListener: function () {},
        removeEventListener: function () {},
        dispatchEvent: function () { return true; },
        cloneNode: function () { return doc.createElement(tagName); },
        querySelector: function () { return null; },
        querySelectorAll: function () { return []; },
        getBoundingClientRect: function () { return { top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0, x: 0, y: 0 }; },
        contains: function () { return false; },
        focus: function () {},
        blur: function () {},
        click: function () {},
        scrollIntoView: function () {},
        scrollIntoViewIfNeeded: function () {},

        // Canvas-specific properties (set when tag === 'canvas')
        width: 300,
        height: 150,
      };

      if (tag === 'canvas') {
        // Set proper prototype chain: HTMLCanvasElement → HTMLElement → Element
        Object.setPrototypeOf(el, root.HTMLCanvasElement.prototype);
        el.getContext = function (contextType) {
          if (contextType === '2d') {
            var ctx = buildCanvas2DContext(el);
            Object.setPrototypeOf(ctx, root.CanvasRenderingContext2D.prototype);
            return ctx;
          }
          if (contextType === 'webgl' || contextType === 'experimental-webgl' || contextType === 'webgl2') {
            var gl = buildWebGLContext();
            Object.setPrototypeOf(gl, root.WebGLRenderingContext.prototype);
            return gl;
          }
          return null;
        };
      }

      if (tag === 'script') {
        el.src = '';
        el.async = true;
        el.defer = false;
      }

      return el;
    };

    doc.getElementsByTagName = function (tagName) {
      if (tagName === 'head') return [{ appendChild: function () { return {}; }, style: {} }];
      return [];
    };

    doc.querySelector = function () { return null; };
    doc.querySelectorAll = function () { return []; };
    doc.getElementById = function () { return null; };
    doc.getElementsByClassName = function () { return []; };
    doc.getElementsByName = function () { return []; };

    doc.createDocumentFragment = function () { return { appendChild: function (c) { return c; }, children: [] }; };
    doc.createTextNode = function (text) { return { textContent: text, nodeType: 3 }; };
    doc.createComment = function () { return { nodeType: 8 }; };

    doc.hasFocus = function () { return true; };
    doc.execCommand = function () { return false; };

    // For document.all detection (anti-bot check)
    var allCol = [undefined];
    allCol.item = function (i) { return undefined; };
    allCol.namedItem = function () { return undefined; };
    Object.defineProperty(doc, 'all', {
      get: function () { return allCol; },
      enumerable: true, configurable: true
    });

    return doc;
  }

  // ============================================================
  // 8. XMLHttpRequest
  // ============================================================
  function buildXMLHttpRequest() {
    var XHR = function () {
      this.readyState = 0;
      this.status = 0;
      this.statusText = '';
      this.responseText = '';
      this.response = '';
      this.responseType = '';
      this.timeout = 0;
      this.withCredentials = false;
      this._headers = {};
      this._method = '';
      this._url = '';
    };

    XHR.prototype = {
      UNSENT: 0, OPENED: 1, HEADERS_RECEIVED: 2, LOADING: 3, DONE: 4,
      readyState: 0,

      open: function (method, url, async) {
        this._method = method;
        this._url = url;
        this.readyState = 1;
        if (this.onreadystatechange) this.onreadystatechange();
      },

      setRequestHeader: function (name, value) {
        this._headers[name] = value;
      },

      send: function (body) {
        // Try to make a real request using Node.js HTTP
        try {
          var self = this;
          var http = require('http');
          var https = require('https');
          var urlModule = require('url');
          var parsed = urlModule.parse(this._url);
          var mod = parsed.protocol === 'https:' ? https : http;

          // Auto-attach cookies for ALL JD domains (token server needs auth)
          var reqHeaders = Object.assign({}, this._headers);
          var isJdDomain = parsed.hostname && (parsed.hostname.endsWith('.jd.com') || parsed.hostname === 'jd.com');
          if (isJdDomain) {
            reqHeaders['Cookie'] = REAL.cookie;
          }

          var options = {
            hostname: parsed.hostname,
            port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
            path: parsed.path,
            method: this._method,
            headers: reqHeaders,
            rejectUnauthorized: false,
          };

          var req = mod.request(options, function (res) {
            self.status = res.statusCode;
            self.statusText = res.statusMessage;
            self.readyState = 2;
            if (self.onreadystatechange) self.onreadystatechange();
            self.readyState = 3;
            if (self.onreadystatechange) self.onreadystatechange();

            var chunks = [];
            res.on('data', function (chunk) { chunks.push(chunk); });
            res.on('end', function () {
              self.responseText = Buffer.concat(chunks).toString('utf8');
              self.response = self.responseText;
              self.readyState = 4;
              if (self.onreadystatechange) self.onreadystatechange();
              if (self.onload) self.onload();
              if (self.onloadend) self.onloadend();
            });
          });

          req.on('error', function (err) {
            self.status = 0;
            self.readyState = 4;
            self.responseText = '';
            if (self.onerror) self.onerror(err);
            if (self.onloadend) self.onloadend();
          });

          if (body) req.write(body);
          req.end();
        } catch (e) {
          // Network unavailable — simulate empty response
          this.status = 200;
          this.readyState = 4;
          this.responseText = '{}';
          this.response = '{}';
          if (this.onreadystatechange) this.onreadystatechange();
          if (this.onload) this.onload();
          if (this.onloadend) this.onloadend();
        }
      },

      abort: function () {},
      getResponseHeader: function (name) { return null; },
      getAllResponseHeaders: function () { return ''; },
      overrideMimeType: function () {},

      onreadystatechange: null,
      onload: null,
      onerror: null,
      onloadend: null,
      ontimeout: null,
    };

    return XHR;
  }

  // ============================================================
  // 9. Crypto
  // ============================================================
  // Deterministic PRNG state (seeded for stable fingerprint)
  var _prngState = 0xDEADBEEF;
  function _prngNext() {
    _prngState = ((_prngState * 1103515245) + 12345) >>> 0;
    return _prngState;
  }

  function buildCrypto() {
    // Use Node.js native crypto for full Web Crypto API
    try {
      var nodeCrypto = require('crypto');

      // --- Web Crypto subtle implementation ---
      var subtle = {
        digest: function (algorithm, data) {
          var algo = (algorithm && algorithm.name || algorithm || 'SHA-256').replace('-', '').toLowerCase();
          return Promise.resolve(nodeCrypto.createHash(algo).update(new Uint8Array(data)).digest());
        },

        importKey: function (format, keyData, algorithm, extractable, keyUsages) {
          try {
            if (format === 'jwk') {
              var opts = { key: keyData, format: 'jwk' };
              var isPrivate = keyData.d || keyData.key_ops || false;
              var key = isPrivate ? nodeCrypto.createPrivateKey(opts) : nodeCrypto.createPublicKey(opts);
              return Promise.resolve({ type: isPrivate ? 'private' : 'public', algorithm: algorithm, extractable: !!extractable, usages: keyUsages || [], _handle: key });
            }
            if (format === 'spki') {
              var buf = Buffer.from(keyData);
              var key = nodeCrypto.createPublicKey({ key: buf, format: 'der', type: 'spki' });
              return Promise.resolve({ type: 'public', algorithm: algorithm, extractable: !!extractable, usages: keyUsages || [], _handle: key });
            }
            if (format === 'pkcs8') {
              var buf = Buffer.from(keyData);
              var key = nodeCrypto.createPrivateKey({ key: buf, format: 'der', type: 'pkcs8' });
              return Promise.resolve({ type: 'private', algorithm: algorithm, extractable: !!extractable, usages: keyUsages || [], _handle: key });
            }
            if (format === 'raw') {
              var buf = Buffer.from(keyData);
              var key = nodeCrypto.createSecretKey(buf);
              return Promise.resolve({ type: 'secret', algorithm: algorithm, extractable: !!extractable, usages: keyUsages || [], _handle: key });
            }
          } catch (e) {
            return Promise.reject(new Error('importKey failed: ' + e.message));
          }
          return Promise.reject(new Error('Unsupported format: ' + format));
        },

        exportKey: function (format, key) {
          try {
            if (format === 'jwk') {
              var exported = key._handle.export({ format: 'jwk' });
              return Promise.resolve(exported);
            }
            if (format === 'spki') {
              var buf = key._handle.export({ format: 'der', type: 'spki' });
              return Promise.resolve(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
            }
            if (format === 'raw') {
              var buf = key._handle.export({ format: 'buffer' });
              return Promise.resolve(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
            }
          } catch (e) {
            return Promise.reject(new Error('exportKey failed: ' + e.message));
          }
          return Promise.reject(new Error('Unsupported export format: ' + format));
        },

        sign: function (algorithm, key, data) {
          try {
            var algoName = algorithm && algorithm.name;
            var buf = Buffer.from(data);

            if (algoName === 'ECDSA') {
              var hash = (algorithm.hash && algorithm.hash.name || 'SHA-256').replace('-', '').toLowerCase();
              var sig = nodeCrypto.sign(hash, buf, { key: key._handle, dsaEncoding: 'ieee-p1363' });
              return Promise.resolve(sig.buffer.slice(sig.byteOffset, sig.byteOffset + sig.byteLength));
            }
            if (algoName === 'HMAC') {
              var hash = (algorithm.hash && algorithm.hash.name || 'SHA-256').replace('-', '').toLowerCase();
              var hmac = nodeCrypto.createHmac(hash, key._handle);
              hmac.update(buf);
              return Promise.resolve(hmac.digest().buffer);
            }
            if (algoName === 'RSASSA-PKCS1-v1_5') {
              var sig = nodeCrypto.sign('sha256', buf, { key: key._handle, padding: nodeCrypto.constants.RSA_PKCS1_PADDING });
              return Promise.resolve(sig.buffer.slice(sig.byteOffset, sig.byteOffset + sig.byteLength));
            }
            if (algoName === 'RSA-PSS') {
              var saltLen = algorithm.saltLength || 32;
              var sig = nodeCrypto.sign('sha256', buf, { key: key._handle, padding: nodeCrypto.constants.RSA_PKCS1_PSS_PADDING, saltLength: saltLen });
              return Promise.resolve(sig.buffer.slice(sig.byteOffset, sig.byteOffset + sig.byteLength));
            }
          } catch (e) {
            return Promise.reject(new Error('sign failed: ' + e.message));
          }
          return Promise.reject(new Error('Unsupported algorithm: ' + (algoName || 'unknown')));
        },

        verify: function (algorithm, key, signature, data) {
          try {
            var algoName = algorithm && algorithm.name;
            var sigBuf = Buffer.from(signature);
            var dataBuf = Buffer.from(data);

            if (algoName === 'ECDSA') {
              var hash = (algorithm.hash && algorithm.hash.name || 'SHA-256').replace('-', '').toLowerCase();
              var result = nodeCrypto.verify(hash, dataBuf, { key: key._handle, dsaEncoding: 'ieee-p1363' }, sigBuf);
              return Promise.resolve(result);
            }
            if (algoName === 'HMAC') {
              var hash = (algorithm.hash && algorithm.hash.name || 'SHA-256').replace('-', '').toLowerCase();
              var hmac = nodeCrypto.createHmac(hash, key._handle);
              hmac.update(dataBuf);
              var expected = hmac.digest();
              return Promise.resolve(nodeCrypto.timingSafeEqual(sigBuf, expected));
            }
            if (algoName === 'RSASSA-PKCS1-v1_5') {
              var result = nodeCrypto.verify('sha256', dataBuf, { key: key._handle, padding: nodeCrypto.constants.RSA_PKCS1_PADDING }, sigBuf);
              return Promise.resolve(result);
            }
            if (algoName === 'RSA-PSS') {
              var result = nodeCrypto.verify('sha256', dataBuf, { key: key._handle, padding: nodeCrypto.constants.RSA_PKCS1_PSS_PADDING, saltLength: algorithm.saltLength || 32 }, sigBuf);
              return Promise.resolve(result);
            }
          } catch (e) {
            return Promise.reject(new Error('verify failed: ' + e.message));
          }
          return Promise.reject(new Error('Unsupported algorithm: ' + (algoName || 'unknown')));
        },

        generateKey: function (algorithm, extractable, keyUsages) {
          try {
            var algoName = algorithm && algorithm.name;
            if (algoName === 'ECDSA' || algoName === 'ECDH') {
              var curve = (algorithm.namedCurve || 'P-256').replace('P-', 'prime');
              var keypair = nodeCrypto.generateKeyPairSync('ec', { namedCurve: curve });
              return Promise.resolve({
                publicKey: { type: 'public', algorithm: algorithm, extractable: true, usages: ['verify'], _handle: keypair.publicKey },
                privateKey: { type: 'private', algorithm: algorithm, extractable: !!extractable, usages: keyUsages || ['sign'], _handle: keypair.privateKey }
              });
            }
            if (algoName === 'HMAC') {
              var key = nodeCrypto.generateKeySync('hmac', { length: (algorithm.length || 256) / 8 });
              return Promise.resolve({ type: 'secret', algorithm: algorithm, extractable: !!extractable, usages: keyUsages || ['sign', 'verify'], _handle: key });
            }
            if (algoName === 'AES-GCM' || algoName === 'AES-CBC' || algoName === 'AES-CTR') {
              var key = nodeCrypto.generateKeySync('aes', { length: algorithm.length || 256 });
              return Promise.resolve({ type: 'secret', algorithm: algorithm, extractable: !!extractable, usages: keyUsages || ['encrypt', 'decrypt'], _handle: key });
            }
          } catch (e) {
            return Promise.reject(new Error('generateKey failed: ' + e.message));
          }
          return Promise.reject(new Error('Unsupported algorithm: ' + (algoName || 'unknown')));
        },

        encrypt: function (algorithm, key, data) {
          try {
            var algoName = algorithm && algorithm.name;
            var buf = Buffer.from(data);
            if (algoName === 'AES-GCM') {
              var iv = Buffer.from(algorithm.iv || new Uint8Array(12));
              var tagLen = algorithm.tagLength || 128;
              var cipher = nodeCrypto.createCipheriv('aes-256-gcm', key._handle, iv, { authTagLength: tagLen / 8 });
              var aad = algorithm.additionalData ? Buffer.from(algorithm.additionalData) : undefined;
              if (aad) cipher.setAAD(aad);
              var encrypted = Buffer.concat([cipher.update(buf), cipher.final()]);
              var tag = cipher.getAuthTag();
              return Promise.resolve(Buffer.concat([encrypted, tag]).buffer);
            }
            if (algoName === 'AES-CBC') {
              var iv = Buffer.from(algorithm.iv || new Uint8Array(16));
              var cipher = nodeCrypto.createCipheriv('aes-256-cbc', key._handle, iv);
              var encrypted = Buffer.concat([cipher.update(buf), cipher.final()]);
              return Promise.resolve(encrypted.buffer);
            }
          } catch (e) {
            return Promise.reject(new Error('encrypt failed: ' + e.message));
          }
          return Promise.reject(new Error('Unsupported algorithm: ' + (algoName || 'unknown')));
        },

        decrypt: function (algorithm, key, data) {
          try {
            var algoName = algorithm && algorithm.name;
            var buf = Buffer.from(data);
            if (algoName === 'AES-GCM') {
              var iv = Buffer.from(algorithm.iv || new Uint8Array(12));
              var tagLen = algorithm.tagLength || 128;
              var tag = buf.slice(buf.length - tagLen / 8);
              var encrypted = buf.slice(0, buf.length - tagLen / 8);
              var decipher = nodeCrypto.createDecipheriv('aes-256-gcm', key._handle, iv, { authTagLength: tagLen / 8 });
              decipher.setAuthTag(tag);
              var aad = algorithm.additionalData ? Buffer.from(algorithm.additionalData) : undefined;
              if (aad) decipher.setAAD(aad);
              var decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);
              return Promise.resolve(decrypted.buffer);
            }
            if (algoName === 'AES-CBC') {
              var iv = Buffer.from(algorithm.iv || new Uint8Array(16));
              var decipher = nodeCrypto.createDecipheriv('aes-256-cbc', key._handle, iv);
              var decrypted = Buffer.concat([decipher.update(buf), decipher.final()]);
              return Promise.resolve(decrypted.buffer);
            }
          } catch (e) {
            return Promise.reject(new Error('decrypt failed: ' + e.message));
          }
          return Promise.reject(new Error('Unsupported algorithm: ' + (algoName || 'unknown')));
        },

        deriveBits: function (algorithm, baseKey, length) {
          return Promise.reject(new Error('deriveBits not implemented'));
        },

        deriveKey: function (algorithm, baseKey, derivedKeyAlgorithm, extractable, keyUsages) {
          return Promise.reject(new Error('deriveKey not implemented'));
        },

        wrapKey: function (format, key, wrappingKey, wrapAlgorithm) {
          return Promise.reject(new Error('wrapKey not implemented'));
        },

        unwrapKey: function (format, wrappedKey, unwrappingKey, unwrapAlgorithm, unwrappedKeyAlgorithm, extractable, keyUsages) {
          return Promise.reject(new Error('unwrapKey not implemented'));
        },
      };
    } catch (e) {
      var subtle = {};
    }

    return {
      subtle: subtle || {},
      getRandomValues: function (array) {
        // Deterministic PRNG — produces stable fingerprint across runs
        if (array) {
          for (var i = 0; i < array.length; i++) {
            _prngNext();
            array[i] = _prngState & 0xFF;
          }
        }
        return array;
      },
      randomUUID: function () {
        // Deterministic UUID for stable fingerprint
        var hex = '0123456789abcdef';
        var uuid = '';
        for (var i = 0; i < 36; i++) {
          if (i === 8 || i === 13 || i === 18 || i === 23) { uuid += '-'; }
          else if (i === 14) { uuid += '4'; }
          else if (i === 19) { _prngNext(); uuid += hex[((_prngState & 0xFF) & 0x3) | 0x8]; }
          else { _prngNext(); uuid += hex[_prngState & 0xF]; _prngNext(); }
        }
        return uuid;
      },
    };
  }

  // ============================================================
  // 10. Window (root)
  // ============================================================
  var doc = buildDocument();
  var nav = buildNavigator();
  var scr = buildScreen();
  var loc = buildLocation();
  var ls = buildStorage();
  var ss = buildStorage();
  var crypto = buildCrypto();
  var XHR = buildXMLHttpRequest();

  // Window = root
  if (typeof root.window === 'undefined') root.window = root;
  root.document = doc;
  root.navigator = nav;
  root.screen = scr;
  root.location = loc;
  root.localStorage = ls;
  root.sessionStorage = ss;
  root.crypto = crypto;
  root.msCrypto = crypto;
  root.XMLHttpRequest = XHR;

  // Window constructor and prototype
  if (typeof root.Window === 'undefined') root.Window = function Window() {};
  root.Window.prototype = root;

  // Document constructor
  if (typeof root.Document === 'undefined') root.Document = function Document() {};
  root.Document.prototype = doc;

  // EventTarget (root of DOM event hierarchy)
  if (typeof root.EventTarget === 'undefined') root.EventTarget = function EventTarget() {};
  root.EventTarget.prototype = {
    addEventListener: function () {},
    removeEventListener: function () {},
    dispatchEvent: function () { return true; },
  };
  root.EventTarget.prototype.constructor = root.EventTarget;

  // Node (extends EventTarget)
  if (typeof root.Node === 'undefined') root.Node = function Node() {};
  root.Node.prototype = Object.create(root.EventTarget.prototype);
  root.Node.prototype.constructor = root.Node;

  // Element (extends Node)
  if (typeof root.Element === 'undefined') root.Element = function Element() {};
  root.Element.prototype = Object.create(root.Node.prototype);
  root.Element.prototype.constructor = root.Element;
  Object.assign(root.Element.prototype, {
    style: {},
    setAttribute: function () {},
    getAttribute: function () { return null; },
    appendChild: function (c) { return c; },
    removeChild: function () { return {}; },
    getBoundingClientRect: function () { return { top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 }; },
    scrollIntoView: function () {},
    scrollIntoViewIfNeeded: function () {},
  });

  // HTMLElement (extends Element)
  if (typeof root.HTMLElement === 'undefined') root.HTMLElement = function HTMLElement() {};
  root.HTMLElement.prototype = Object.create(root.Element.prototype);
  root.HTMLElement.prototype.constructor = root.HTMLElement;

  // HTMLCanvasElement (extends HTMLElement)
  if (typeof root.HTMLCanvasElement === 'undefined') root.HTMLCanvasElement = function HTMLCanvasElement() {};
  root.HTMLCanvasElement.prototype = Object.create(root.HTMLElement.prototype);
  root.HTMLCanvasElement.prototype.constructor = root.HTMLCanvasElement;
  root.HTMLCanvasElement.prototype.getContext = function () { return null; };
  root.HTMLCanvasElement.prototype.toDataURL = function () { return 'data:,'; };
  root.HTMLCanvasElement.prototype.toBlob = function () {};

  // CanvasRenderingContext2D
  if (typeof root.CanvasRenderingContext2D === 'undefined') root.CanvasRenderingContext2D = function CanvasRenderingContext2D() {};

  // WebGLRenderingContext
  if (typeof root.WebGLRenderingContext === 'undefined') root.WebGLRenderingContext = function WebGLRenderingContext() {};

  // Symbol.toStringTag
  try {
    Object.defineProperty(root.HTMLCanvasElement.prototype, Symbol.toStringTag, { value: 'HTMLCanvasElement' });
    Object.defineProperty(root.CanvasRenderingContext2D.prototype, Symbol.toStringTag, { value: 'CanvasRenderingContext2D' });
    Object.defineProperty(root.WebGLRenderingContext.prototype, Symbol.toStringTag, { value: 'WebGLRenderingContext' });
  } catch (e) {}

  // Navigator constructor
  if (typeof root.Navigator === 'undefined') root.Navigator = function Navigator() {};
  root.Navigator.prototype = nav;

  // Location constructor
  if (typeof root.Location === 'undefined') root.Location = function Location() {};
  root.Location.prototype = loc;

  // Storage constructor
  if (typeof root.Storage === 'undefined') root.Storage = function Storage() {};
  root.Storage.prototype = ls;

  // Window specific properties
  root.innerWidth = REAL.innerW;
  root.innerHeight = REAL.innerH;
  root.outerWidth = REAL.outerW;
  root.outerHeight = REAL.outerH;
  root.devicePixelRatio = REAL.devicePixelRatio;
  root.chrome = { runtime: {}, loadTimes: function () {}, csi: function () {} };
  root.top = root;
  root.self = root;
  root.parent = root;
  root.name = '';
  root.closed = false;
  root.opener = null;
  root.frames = root;
  root.length = 0;
  root.scrollX = 0;
  root.scrollY = 0;
  root.pageXOffset = 0;
  root.pageYOffset = 0;

  // Micro-app stubs (must be undefined, not absent)
  root.__MICRO_APP_ENVIRONMENT_TEMPORARY__ = undefined;
  root.__MICRO_APP_ENVIRONMENT__ = undefined;
  root.__MICRO_APP_PROXY_WINDOW__ = undefined;
  root.__MICRO_APP_BASE_APPLICATION__ = undefined;
  root.rawWindow = undefined;

  // JD specific
  root.__JDWEBSIGNHELPER_$DATA__ = root.__JDWEBSIGNHELPER_$DATA__ || {};

  // getComputedStyle
  root.getComputedStyle = function () {
    return {
      getPropertyValue: function () { return ''; },
      getPropertyCSSValue: function () { return null; },
    };
  };

  // requestAnimationFrame
  if (typeof root.requestAnimationFrame === 'undefined') {
    root.requestAnimationFrame = function (cb) { return root.setTimeout ? root.setTimeout(cb, 16) : 0; };
    root.cancelAnimationFrame = function (id) { if (root.clearTimeout) root.clearTimeout(id); };
  }

  // fetch
  if (typeof root.fetch === 'undefined') {
    root.fetch = function (url, options) {
      return new root.Promise(function (resolve) {
        try {
          var xhr = new XHR();
          xhr.open((options && options.method) || 'GET', url);
          xhr.onload = function () {
            resolve({
              ok: xhr.status >= 200 && xhr.status < 300,
              status: xhr.status,
              statusText: xhr.statusText,
              text: function () { return root.Promise.resolve(xhr.responseText); },
              json: function () { return root.Promise.resolve(JSON.parse(xhr.responseText || '{}')); },
              headers: new Map(),
            });
          };
          xhr.onerror = function () {
            resolve({ ok: false, status: 0, text: function () { return root.Promise.resolve(''); } });
          };
          xhr.send(options && options.body);
        } catch (e) {
          resolve({ ok: false, status: 0, text: function () { return root.Promise.resolve(''); } });
        }
      });
    };
  }

  // Console
  if (typeof root.console === 'undefined') root.console = {};
  ['log', 'info', 'warn', 'error', 'debug', 'trace'].forEach(function (m) {
    if (typeof root.console[m] !== 'function') root.console[m] = function () {};
  });

  // requestIdleCallback
  if (typeof root.requestIdleCallback === 'undefined') {
    root.requestIdleCallback = function (cb) { return root.setTimeout(function () { cb({ didTimeout: false, timeRemaining: function () { return 50; } }); }, 1); };
  }

  // atob / btoa
  if (typeof root.atob === 'undefined') {
    root.atob = function (str) { return Buffer.from(str, 'base64').toString('binary'); };
    root.btoa = function (str) { return Buffer.from(str, 'binary').toString('base64'); };
  }

  // Performance (fixed values for deterministic fingerprint)
  root.performance = {
    now: function () { return 709481.1; },
    timing: { navigationStart: 1785407536000, loadEventEnd: 1785407537000, domComplete: 1785407536500 },
    memory: { jsHeapSizeLimit: 4395630592, totalJSHeapSize: 62808730, usedJSHeapSize: 36295934 },
    getEntries: function () { return []; },
    getEntriesByType: function () { return []; },
    mark: function () {},
    measure: function () {},
  };

  // matchMedia
  root.matchMedia = function (query) {
    return {
      matches: false,
      media: query,
      onchange: null,
      addListener: function () {},
      removeListener: function () {},
      addEventListener: function () {},
      removeEventListener: function () {},
      dispatchEvent: function () { return true; },
    };
  };

  // Intl
  if (typeof root.Intl === 'undefined') {
    root.Intl = {
      DateTimeFormat: function () {
        return {
          resolvedOptions: function () { return { timeZone: REAL.timezone, locale: REAL.language }; },
          format: function (d) { return d.toString(); },
        };
      },
    };
  }

}(typeof globalThis !== 'undefined' ? globalThis : this));
