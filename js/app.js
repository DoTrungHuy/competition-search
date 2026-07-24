/**
 * 竞赛列表、筛选和可访问详情抽屉。
 */
(function () {
  "use strict";

  var state = {
    items: [],
    brands: {},
    query: "",
    quick: "",
  };
  var lastFocused = null;

  var KIND_CLASSES = {
    全国赛事: "badge-kind-national",
    大厂赛事: "badge-kind-corporate",
    国际赛事: "badge-kind-international",
    校级赛事: "badge-kind-campus",
  };

  var STATUS_CLASSES = {
    报名中: "badge-status-open",
    即将开始报名: "badge-status-upcoming",
    即将开始: "badge-status-upcoming",
    进行中: "badge-status-running",
    报名结束: "badge-status-closed",
    已结束: "badge-status-ended",
    已停办: "badge-status-ended",
  };

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/'/g, "&#39;");
  }

  function kindClass(kind) {
    return KIND_CLASSES[kind] || "badge-kind-national";
  }

  function statusClass(status, urgent) {
    if (urgent) return "badge badge-urgent";
    return "badge " + (STATUS_CLASSES[status] || "badge-status-ended");
  }

  function brandFor(item) {
    return state.brands[item.brand_id] || null;
  }

  function sourceLink(item) {
    var brand = brandFor(item);
    return item.link || (brand && brand.official_home) || "";
  }

  function sourceLabel(item) {
    return item.link ? "查看原文" : "赛事主页";
  }

  function timeLine(item) {
    if (item.needs_review === true) return "见官网详情";
    var status = window.CompStatus.computeStatus(item).status;
    if (status === "即将开始报名" && item.registration_start) {
      if (item.registration_end) {
        return (
          "报名开始 " +
          item.registration_start +
          "，截止 " +
          item.registration_end
        );
      }
      return "报名开始 " + item.registration_start;
    }
    if (status === "即将开始" && item.competition_start) {
      if (item.competition_end) {
        return "比赛 " + item.competition_start + " 至 " + item.competition_end;
      }
      return "比赛开始 " + item.competition_start;
    }
    if (
      status === "进行中" &&
      item.competition_start &&
      item.competition_end
    ) {
      return "比赛 " + item.competition_start + " 至 " + item.competition_end;
    }
    if (status === "已结束" && item.competition_end) {
      return "比赛结束 " + item.competition_end;
    }
    if (item.registration_start && item.registration_end) {
      return "报名 " + item.registration_start + " 至 " + item.registration_end;
    }
    if (item.registration_end) return "报名截止 " + item.registration_end;
    if (item.competition_start && item.competition_end) {
      return "比赛 " + item.competition_start + " 至 " + item.competition_end;
    }
    if (item.competition_end) return "比赛结束 " + item.competition_end;
    if (item.competition_start) return "比赛开始 " + item.competition_start;
    if (item.published_at) return "通知发布 " + item.published_at;
    return "见官网详情";
  }

  var GENERIC_REQUIREMENT = {
    以活动页面为准: true,
    以赛题页面为准: true,
    以通知原文为准: true,
    open: true,
    详见官网: true,
    见官网详情: true,
  };

  function requirementLine(item) {
    var eligibility = String(item.eligibility || "").trim();
    if (eligibility && !GENERIC_REQUIREMENT[eligibility]) {
      return eligibility;
    }
    if (item.team_size) return item.team_size;
    // 套话要求不直接展示；尽量用已有字段拼出可区分的一行
    var brand = brandFor(item);
    var brandName = brand && brand.name ? brand.name : "";
    if (item.organizer) {
      return "主办 " + item.organizer + "；细则见官网";
    }
    if (brandName && item.name) {
      return brandName + "「" + item.name + "」；细则见官网";
    }
    if (item.name) return "「" + item.name + "」细则见官网";
    return "";
  }

  function normalize(item) {
    var kind = item.kind;
    var channel = item.info_channel;
    if (!kind && item.source) {
      if (item.source === "南邮通知") {
        kind = "全国赛事";
        channel = channel || "校内官网";
      } else if (item.source === "国际黑客松") {
        kind = "国际赛事";
        channel = channel || "平台聚合";
      } else {
        kind = item.source;
        channel = channel || "官方渠道";
      }
    }
    return Object.assign({}, item, {
      kind: kind || "全国赛事",
      info_channel: channel || "官方渠道",
    });
  }

  function enrich(item) {
    var base = normalize(item);
    var statusMeta = window.CompStatus.computeStatus(base);
    return Object.assign({}, base, {
      _status: statusMeta.status,
      _urgent: statusMeta.urgent,
      _statusMeta: statusMeta,
    });
  }

  function matchesQuery(item, query) {
    if (!query) return true;
    var brand = brandFor(item);
    var blob = [
      item.name,
      item.description,
      item.organizer,
      item.kind,
      item.info_channel,
      item.edition,
      brand && brand.name,
      brand && (brand.aliases || []).join(" "),
      (item.tags || []).join(" "),
      (item.category || []).join(" "),
    ]
      .join(" ")
      .toLowerCase();
    return blob.indexOf(query) !== -1;
  }

  function isInternational(item) {
    return item.kind === "国际赛事";
  }

  /**
   * 主栏（全部 / 全国 / 大厂 / 状态筛选）不展示国际赛事；
   * 国际赛单独芯片；搜索有关键词时仍可命中国际赛事。
   */
  function inMainLane(item) {
    return !isInternational(item);
  }

  function filterItems() {
    var query = state.query.trim().toLowerCase();
    var list = state.items.map(enrich).filter(function (item) {
      if (item.active === false) return false;
      if (
        window.CompStatus.withinTwoYears &&
        !window.CompStatus.withinTwoYears(item)
      ) {
        return false;
      }

      if (state.quick === "国际") {
        if (!isInternational(item)) return false;
      } else if (state.quick === "大厂") {
        if (item.kind !== "大厂赛事") return false;
      } else if (state.quick === "全国") {
        if (item.kind !== "全国赛事") return false;
      } else if (state.quick === "报名中") {
        // 含即将截止：排序里紧急项仍靠前，不再单独设「快截止」芯片
        if (!inMainLane(item) || item._status !== "报名中") return false;
      } else if (state.quick === "即将开始报名") {
        if (!inMainLane(item) || item._status !== "即将开始报名") return false;
      } else if (state.quick === "进行中") {
        if (!inMainLane(item) || item._status !== "进行中") return false;
      } else {
        // 全部：默认主栏不含国际赛；有搜索词时放行国际赛，便于检索
        if (!query && !inMainLane(item)) return false;
      }

      return matchesQuery(item, query);
    });

    list.sort(function (a, b) {
      return window.CompStatus.compareCompetitions(a, b);
    });
    return list;
  }

  function renderList() {
    var list = filterItems();
    var root = $("list");
    root.setAttribute("aria-busy", "false");
    $("result-meta").textContent = "找到 " + list.length + " 项";
    root.innerHTML = "";

    if (!list.length) {
      var emptyHint =
        state.quick === "即将开始报名"
          ? "当前没有已核验的「报名开始日」仍在未来的赛事；有官网日期后会自动显示"
          : state.quick === "国际"
            ? "当前没有符合条件的国际赛；可清空搜索或切回「全部」查看国内主栏"
            : "可以清空搜索、切换「国际赛」或回到「全部」";
      root.innerHTML =
        '<div class="empty liquid-glass"><p>没有符合条件的竞赛</p><p>' +
        emptyHint +
        '</p><button type="button" class="btn-white" id="btn-reset">清空条件</button></div>';
      var resetButton = $("btn-reset");
      if (resetButton) resetButton.addEventListener("click", resetFilters);
      return;
    }

    list.forEach(function (item, index) {
      var card = document.createElement("article");
      card.className = "card bloom-card liquid-glass";
      card.style.animationDelay = Math.min(index, 8) * 0.04 + "s";

      var statusLabel = item._urgent ? "即将截止" : item._status;
      var statusBadge =
        item._status === "待复核"
          ? ""
          : '<span class="' +
            statusClass(item._status, item._urgent) +
            '">' +
            escapeHtml(statusLabel) +
            "</span>";
      var requirement = requirementLine(item);
      var link = sourceLink(item);
      var linkLabel = sourceLabel(item);
      var channelNote =
        item.info_channel === "校内官网"
          ? '<p class="card-line card-line--muted">学校网站有相关通知</p>'
          : "";

      card.innerHTML =
        '<div class="card-top">' +
        '<h3 class="card-title">' +
        escapeHtml(item.name) +
        "</h3>" +
        '<div class="badges">' +
        '<span class="badge ' +
        kindClass(item.kind) +
        '">' +
        escapeHtml(item.kind) +
        "</span>" +
        statusBadge +
        "</div></div>" +
        '<div class="card-facts">' +
        '<p class="card-line"><span class="card-label">时间</span>' +
        escapeHtml(timeLine(item)) +
        "</p>" +
        (requirement
          ? '<p class="card-line"><span class="card-label">要求</span>' +
            escapeHtml(requirement) +
            "</p>"
          : "") +
        channelNote +
        "</div>" +
        '<div class="card-actions">' +
        (link
          ? '<a class="btn-white" href="' +
            escapeAttr(link) +
            '" target="_blank" rel="noopener noreferrer">' +
            escapeHtml(linkLabel) +
            "</a>"
          : "") +
        '<button type="button" class="btn-ghost" data-detail>更多信息</button>' +
        "</div>";

      card
        .querySelector("[data-detail]")
        .addEventListener("click", function (event) {
          openDrawer(item, event.currentTarget);
        });
      root.appendChild(card);
    });
  }

  function setBackgroundInert(inert) {
    document.querySelectorAll(".topbar, .wrap").forEach(function (element) {
      if (inert) element.setAttribute("inert", "");
      else element.removeAttribute("inert");
    });
  }

  function drawerFocusable() {
    return Array.prototype.slice.call(
      $("drawer").querySelectorAll(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    );
  }

  function openDrawer(item, trigger) {
    var enriched = enrich(item);
    var link = sourceLink(item);
    var statusSection =
      enriched._status === "待复核"
        ? ""
        : '<div class="drawer-section"><strong>状态</strong>' +
          escapeHtml(enriched._urgent ? "即将截止" : enriched._status) +
          "</div>";
    lastFocused = trigger || document.activeElement;

    $("drawer-title").textContent = item.name;
    $("drawer-body").innerHTML =
      '<div class="drawer-section"><strong>类型</strong>' +
      escapeHtml(item.kind) +
      "</div>" +
      statusSection +
      '<div class="drawer-section"><strong>时间</strong>' +
      escapeHtml(timeLine(item)) +
      "</div>" +
      (requirementLine(item)
        ? '<div class="drawer-section"><strong>要求</strong>' +
          escapeHtml(requirementLine(item)) +
          "</div>"
        : "") +
      '<div class="drawer-section"><strong>主办</strong>' +
      escapeHtml(item.organizer || "见原文") +
      "</div>" +
      (item.description
        ? '<div class="drawer-section"><strong>简介</strong>' +
          escapeHtml(item.description) +
          "</div>"
        : "") +
      (item.info_channel === "校内官网"
        ? '<div class="drawer-notice">学校网站发布过相关通知，不代表学校是赛事主办方。</div>'
        : "") +
      (link
        ? '<div class="drawer-section"><a class="btn-white" href="' +
          escapeAttr(link) +
          '" target="_blank" rel="noopener noreferrer">' +
          escapeHtml(sourceLabel(item)) +
          "</a></div>"
        : "");

    $("drawer").classList.add("is-open");
    $("drawer").setAttribute("aria-hidden", "false");
    $("drawer-backdrop").classList.add("is-open");
    $("drawer-backdrop").setAttribute("aria-hidden", "false");
    setBackgroundInert(true);
    document.body.style.overflow = "hidden";
    window.setTimeout(function () {
      $("drawer-close").focus();
    }, 0);
  }

  function closeDrawer() {
    if (!$("drawer").classList.contains("is-open")) return;
    $("drawer").classList.remove("is-open");
    $("drawer").setAttribute("aria-hidden", "true");
    $("drawer-backdrop").classList.remove("is-open");
    $("drawer-backdrop").setAttribute("aria-hidden", "true");
    setBackgroundInert(false);
    document.body.style.overflow = "";
    if (lastFocused && document.contains(lastFocused)) lastFocused.focus();
    lastFocused = null;
  }

  function trapDrawerFocus(event) {
    if (event.key !== "Tab" || !$("drawer").classList.contains("is-open")) {
      return;
    }
    var focusable = drawerFocusable();
    if (!focusable.length) {
      event.preventDefault();
      $("drawer").focus();
      return;
    }
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function syncChips() {
    document.querySelectorAll(".chip").forEach(function (chip) {
      var key = chip.getAttribute("data-quick") || "";
      var selected = key === state.quick;
      chip.classList.toggle("is-on", selected);
      chip.setAttribute("aria-pressed", selected ? "true" : "false");
    });
  }

  function resetFilters() {
    state.query = "";
    state.quick = "";
    $("search-input").value = "";
    $("search-clear").classList.remove("is-visible");
    syncChips();
    renderList();
  }

  function fetchJson(path, bust) {
    var suffix = bust ? "?t=" + Date.now() : "";
    return fetch(path + suffix).then(function (response) {
      if (!response.ok) throw new Error(path + " HTTP " + response.status);
      return response.json();
    });
  }

  function loadData(options) {
    var opts = options || {};
    var banner = $("error-banner");
    if (banner) {
      banner.classList.remove("is-visible");
      banner.textContent = "";
    }
    $("list").setAttribute("aria-busy", "true");

    return Promise.all([
      fetchJson("./data/competitions.json", opts.bust),
      fetchJson("./data/brands.json", opts.bust),
    ])
      .then(function (payloads) {
        state.items = payloads[0].competitions || [];
        state.brands = {};
        (payloads[1].brands || []).forEach(function (brand) {
          state.brands[brand.brand_id] = brand;
        });
        syncChips();
        renderList();
        if (opts.notify && $("reload-status")) {
          $("reload-status").textContent =
            "已刷新，共 " + state.items.length + " 条";
        }
      })
      .catch(function (error) {
        $("list").setAttribute("aria-busy", "false");
        if (banner) {
          banner.textContent =
            "数据加载失败。请使用本地静态服务器打开本站。" +
            (error && error.message ? " " + error.message : "");
          banner.classList.add("is-visible");
        }
        if ($("reload-status")) $("reload-status").textContent = "刷新失败";
      });
  }

  function bind() {
    var search = $("search-input");
    var searchTimer = null;

    search.addEventListener("input", function () {
      var value = search.value;
      $("search-clear").classList.toggle("is-visible", Boolean(value));
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(function () {
        state.query = value;
        renderList();
      }, 180);
    });

    $("search-clear").addEventListener("click", function () {
      search.value = "";
      state.query = "";
      $("search-clear").classList.remove("is-visible");
      renderList();
      search.focus();
    });

    document.querySelectorAll(".chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        state.quick = chip.getAttribute("data-quick") || "";
        syncChips();
        renderList();
      });
    });

    $("btn-reload-data").addEventListener("click", function () {
      var button = $("btn-reload-data");
      button.disabled = true;
      $("reload-status").textContent = "刷新中…";
      loadData({ bust: true, notify: true }).then(function () {
        button.disabled = false;
      });
    });

    $("drawer-close").addEventListener("click", closeDrawer);
    $("drawer-backdrop").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeDrawer();
      trapDrawerFocus(event);
      if (
        event.key === "/" &&
        !$("drawer").classList.contains("is-open") &&
        document.activeElement !== search
      ) {
        event.preventDefault();
        search.focus();
      }
    });
  }

  function init() {
    bind();
    if (window.CompTheme) window.CompTheme.init();
    if (window.CompVisits) window.CompVisits.init();
    if (window.CompParticles) {
      window.CompParticles.start(document.getElementById("particle-canvas"));
    }
    if (window.CompBlurText) window.CompBlurText.initAll();
    loadData();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
