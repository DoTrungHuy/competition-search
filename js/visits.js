/**
 * 页面浏览次数。每次页面加载只向远端计数服务发起一次加一请求。
 *
 * 注意这是「页面浏览次数」而非独立访客数：刷新与爬虫都会计入，
 * 且 CounterAPI v1 是公开无鉴权计数器。真实站点统计以 Cloudflare Web Analytics 为准。
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

  /** 取不到数就整块隐藏：为数字排版的位置塞不下「暂不可用」，也没有展示价值。 */
  function hidePill() {
    var element = $("visit-count");
    if (!element) return;
    var pill = element.closest ? element.closest(".visit-pill") : null;
    (pill || element).hidden = true;
  }

  function showCount(value) {
    var number = Number(value);
    if (!isFinite(number)) {
      hidePill();
      return;
    }
    show(number.toLocaleString("zh-CN"), "页面浏览 " + number);
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
    show("…", "正在读取页面浏览次数");
    remoteCount().then(showCount).catch(hidePill);
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
