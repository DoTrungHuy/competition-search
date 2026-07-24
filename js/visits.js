/**
 * 访问次数。每次页面加载只向远端计数服务发起一次加一请求。
 */
(function (global) {
  "use strict";

  var NAMESPACE = "competition-search";
  var KEY = "pageviews";

  function $(id) {
    return document.getElementById(id);
  }

  function show(value, label) {
    var element = $("visit-count");
    if (!element) return;
    element.textContent = value;
    element.setAttribute("aria-label", label || String(value));
  }

  function showCount(value) {
    var number = Number(value);
    if (!isFinite(number)) {
      show("暂不可用", "访问次数暂不可用");
      return;
    }
    show(number.toLocaleString("zh-CN"), "访问次数 " + number);
  }

  function extractCount(data) {
    if (data == null) return null;
    if (typeof data === "number") return data;
    if (data.value != null) return data.value;
    if (data.count != null) return data.count;
    if (data.data && data.data.up_count != null) return data.data.up_count;
    if (data.data && data.data.count != null) return data.data.count;
    return null;
  }

  function fetchJson(url) {
    return fetch(url, {
      method: "GET",
      mode: "cors",
      cache: "no-store",
    }).then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    });
  }

  function counterUrl() {
    return (
      "https://api.counterapi.dev/v1/" +
      encodeURIComponent(NAMESPACE) +
      "/" +
      encodeURIComponent(KEY) +
      "/up"
    );
  }

  function remoteCount() {
    return fetchJson(counterUrl()).then(function (data) {
      var count = extractCount(data);
      if (count == null) throw new Error("计数接口返回格式不正确");
      return count;
    });
  }

  function init() {
    if (!$("visit-count")) return;
    show("…", "正在读取访问次数");
    remoteCount()
      .then(showCount)
      .catch(function () {
        show("暂不可用", "访问次数暂不可用");
      });
  }

  global.CompVisits = {
    init: init,
    counterUrl: counterUrl,
    extractCount: extractCount,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = global.CompVisits;
  }
})(typeof window !== "undefined" ? window : globalThis);
