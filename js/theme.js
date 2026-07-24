/**
 * 日间 / 夜间主题切换，偏好写入 localStorage
 */
(function (global) {
  var KEY = "compsearch-theme";

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function getStored() {
    try {
      return localStorage.getItem(KEY);
    } catch (e) {
      return null;
    }
  }

  function apply(theme) {
    var previous = document.documentElement.getAttribute("data-theme");
    var t = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", t);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute("content", t === "dark" ? "#0b1220" : "#e8eef8");
    }
    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.setAttribute("aria-pressed", t === "dark" ? "true" : "false");
      btn.setAttribute("aria-label", t === "dark" ? "切换到日间模式" : "切换到夜间模式");
      var label = btn.querySelector(".theme-toggle-label");
      if (label) label.textContent = t === "dark" ? "日间" : "夜间";
      var icon = btn.querySelector(".theme-toggle-icon");
      if (icon) icon.textContent = t === "dark" ? "亮" : "暗";
    }
    if (previous !== t && typeof window.CustomEvent === "function") {
      document.dispatchEvent(
        new CustomEvent("compsearch:themechange", { detail: { theme: t } })
      );
    }
  }

  function init() {
    var stored = getStored();
    var theme = stored === "dark" || stored === "light" ? stored : systemPrefersDark() ? "dark" : "light";
    apply(theme);

    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.addEventListener("click", function () {
        var cur = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
        var next = cur === "dark" ? "light" : "dark";
        try {
          localStorage.setItem(KEY, next);
        } catch (e) {}
        apply(next);
      });
    }
  }

  global.CompTheme = { init: init, apply: apply };
})(typeof window !== "undefined" ? window : globalThis);
