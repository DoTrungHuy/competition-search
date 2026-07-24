/**
 * 简化版 BlurText（对齐 liquidGlassAgency 意图：逐词 blur-in）
 * 无 Framer 依赖，CSS animation + stagger
 */
(function (global) {
  function applyBlurText(el, options) {
    if (!el) return;
    options = options || {};
    var delayStep = options.delayStep != null ? options.delayStep : 100;
    var text = el.getAttribute("data-blur-text") || el.textContent || "";
    text = text.trim();
    if (!text) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.textContent = text;
      return;
    }

    var words = text.split(/\s+/);
    el.textContent = "";
    el.classList.add("blur-text");
    words.forEach(function (w, i) {
      var span = document.createElement("span");
      span.className = "blur-text-word";
      span.textContent = w;
      span.style.animationDelay = (i * delayStep) / 1000 + "s";
      el.appendChild(span);
      if (i < words.length - 1) {
        el.appendChild(document.createTextNode(" "));
      }
    });
  }

  function initAll() {
    document.querySelectorAll("[data-blur-text]").forEach(function (el) {
      applyBlurText(el);
    });
  }

  global.CompBlurText = { apply: applyBlurText, initAll: initAll };
})(typeof window !== "undefined" ? window : globalThis);
