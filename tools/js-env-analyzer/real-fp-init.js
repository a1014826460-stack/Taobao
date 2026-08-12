// Real browser fingerprint + anti-detection injection for Playwright headless
// This runs before any page JS via context.addInitScript()

(function () {
  // --- Hide automation signals ---
  Object.defineProperty(navigator, 'webdriver', { get: function () { return false; } });

  // Override chrome.runtime for headless detection
  window.chrome = window.chrome || { runtime: {}, loadTimes: function () {}, csi: function () {} };

  // Override permissions
  var origQuery = (navigator.permissions || {}).query;
  if (navigator.permissions) {
    navigator.permissions.query = function (params) {
      if (params.name === 'notifications') {
        return Promise.resolve({ state: Notification.permission });
      }
      return origQuery ? origQuery.call(this, params) : Promise.resolve({ state: 'prompt' });
    };
  }

  // --- Real Canvas + WebGL from Chrome 150 Win10 ---
  var REAL_CANVAS_DATAURL = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAARgAAAA8CAYAAAC9xKUYAAAQAElEQVR4AexaC1hV1bYea/MQUBBfKfIIzUyMsBJQSbQvTUvETBOI6xNhb8zTOaV4up3kVt+1urew1K6fbDTtZFdSUSvTVI6pB8V81LlHTdQkUcBSQXkoKo+97j8WbN6g+zMOr7G/NVhrzjnGnGP+c85/jjUXOpKfICAICRUNKI5BKBRSGgpJRQCtoJ5TCQBkEo6qgLklR1JKSG8yRA+w5hRyeMnDokR5cpUqFKADyQVTtQNjgWAlChDoRHwFp9MyGhnVHSE2qV3TgAoXQdLLaRYBocm2p5iSgqIoVSVQSWik2aVEFAGhEqBllwQQPIAgkBzICAE0xyoS5uCQBtFQAimjQ6sdEsQaAkICMG0hFEQHwSBNoqAEEwbHVjpliDQEhAQgmkJoyA+CAJtFAEhmDY6sGnZrUURBK0cASGYVj6A4r4g0FIQEIJpKSMhfmQhYFgIVBFMw0EpVTUVAklBVFqshmRSCLSaCgEBqwiFHTAxM8poYkIsSKhIAAhMBSZYKiRYFCSRBlGkKclggIQyEAcRBKXBkISgI4AQEVaBIJL0pGSEhARKMgqFoKAEhBIVAlAojBBBSBkgAAxg0hAIyVwFBOQCRFBQFCpBRJWrgAhChUwgQBSARaaAqIRgihICJRBIkIAoKCoGihSSogGBBCKLEigMAiAgFcIEFAAoAONMQIMBgCRHSggSqggjAYqGC9FxMKCSASMGl4oMCUVVRIFLoCISApAKoMIgpBMEBgQwjCWSYUEgoBKgkpBBhCkBBAqCSwKoQFKEgxBngQhBCrYmKUo1CpQjAUMCJA4IkUlDBGpASEKCkhUBnELwaqSLEFBCCLwBIwEC1oMKSBoEEYCOQBEBBYiUESCEIQg1EzEgBBQIqCCtAVyJAigoEiwcFAI4oKEBxNpFlMGoEEEIAgdAAEXIEhQFQEJoBSJCAISyoGKAIYJqSIAGQMwQbQDlgHFEiQPAIqQVJBEJDBSgJiqpYiIOkCAsBHMgCZK0RCSEIQAIggEoBgSgEBFJRgGEkooSAIhFAooJEYCSlQIIJhBKQaDAcE";

  // Real WebGL parameters from Chrome 150 / Win10
  var REAL_WEBGL = {
    VENDOR: "WebKit",
    RENDERER: "WebKit WebGL",
    VERSION: "WebGL 1.0 (OpenGL ES 2.0 Chromium)",
    SHADING_LANGUAGE_VERSION: "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
    MAX_TEXTURE_SIZE: 16384,
    MAX_RENDERBUFFER_SIZE: 16384,
    MAX_VIEWPORT_DIMS: [32767, 32767],
    RED_BITS: 8, GREEN_BITS: 8, BLUE_BITS: 8, ALPHA_BITS: 8,
    DEPTH_BITS: 24, STENCIL_BITS: 0,
    MAX_VERTEX_ATTRIBS: 16,
    MAX_VERTEX_UNIFORM_VECTORS: 4096,
    MAX_FRAGMENT_UNIFORM_VECTORS: 1024,
    MAX_VARYING_VECTORS: 30,
    MAX_TEXTURE_IMAGE_UNITS: 16,
    MAX_COMBINED_TEXTURE_IMAGE_UNITS: 32,
    SAMPLES: 4, SUBPIXEL_BITS: 4,
    extensions: ["ANGLE_instanced_arrays","EXT_blend_minmax","EXT_clip_control","EXT_color_buffer_half_float","EXT_depth_clamp","EXT_disjoint_timer_query","EXT_float_blend","EXT_frag_depth","EXT_polygon_offset_clamp","EXT_shader_texture_lod","EXT_texture_compression_bptc","EXT_texture_compression_rgtc","EXT_texture_filter_anisotropic","EXT_texture_mirror_clamp_to_edge","EXT_sRGB","KHR_parallel_shader_compile","OES_element_index_uint","OES_fbo_render_mipmap","OES_standard_derivatives","OES_texture_float","OES_texture_float_linear","OES_texture_half_float","OES_texture_half_float_linear","OES_vertex_array_object","WEBGL_blend_func_extended","WEBGL_color_buffer_float","WEBGL_compressed_texture_s3tc","WEBGL_compressed_texture_s3tc_srgb","WEBGL_debug_renderer_info","WEBGL_debug_shaders","WEBGL_depth_texture","WEBGL_draw_buffers","WEBGL_lose_context","WEBGL_multi_draw","WEBGL_polygon_mode"]
  };

  var GL_CONSTANTS = {
    0x1F00: "VENDOR", 0x1F01: "RENDERER", 0x1F02: "VERSION",
    0x8B8C: "SHADING_LANGUAGE_VERSION", 0x0D33: "MAX_TEXTURE_SIZE",
    0x84E8: "MAX_RENDERBUFFER_SIZE", 0x0D3A: "MAX_VIEWPORT_DIMS",
    0x0D35: "RED_BITS", 0x0D36: "GREEN_BITS", 0x0D37: "BLUE_BITS",
    0x0D38: "ALPHA_BITS", 0x0D39: "DEPTH_BITS", 0x0D3B: "STENCIL_BITS",
    0x8869: "MAX_VERTEX_ATTRIBS", 0x8DFB: "MAX_VERTEX_UNIFORM_VECTORS",
    0x8DFC: "MAX_FRAGMENT_UNIFORM_VECTORS", 0x8B4B: "MAX_VARYING_VECTORS",
    0x8B4C: "MAX_TEXTURE_IMAGE_UNITS", 0x8B4D: "MAX_COMBINED_TEXTURE_IMAGE_UNITS",
    0x80A9: "SAMPLES", 0x80AA: "SUBPIXEL_BITS"
  };

  // Patch Canvas 2D toDataURL
  var origGetContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function () {
    var ctx = origGetContext.apply(this, arguments);
    if (ctx && typeof ctx.toDataURL === 'function') {
      var origToDataURL = ctx.toDataURL;
      ctx.toDataURL = function () { return REAL_CANVAS_DATAURL; };
    }
    return ctx;
  };

  // Patch WebGL getParameter
  var _origCreateElement = document.createElement.bind(document);
  document.createElement = function (tagName) {
    var el = _origCreateElement(tagName);
    if ((tagName || '').toLowerCase() === 'canvas') {
      var _origCanvasGetContext = el.getContext.bind(el);
      el.getContext = function (type) {
        var ctx = _origCanvasGetContext(type);
        if (ctx && (type === 'webgl' || type === 'experimental-webgl' || type === 'webgl2')) {
          var _origGetParam = ctx.getParameter.bind(ctx);
          ctx.getParameter = function (p) {
            var name = GL_CONSTANTS[p];
            if (name && REAL_WEBGL[name] !== undefined) {
              if (name === 'MAX_VIEWPORT_DIMS') return new Int32Array(REAL_WEBGL[name]);
              return REAL_WEBGL[name];
            }
            return _origGetParam(p);
          };
          var _origExts = ctx.getSupportedExtensions.bind(ctx);
          ctx.getSupportedExtensions = function () { return REAL_WEBGL.extensions.slice(); };
        }
        return ctx;
      };
    }
    return el;
  };
})();
