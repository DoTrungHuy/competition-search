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
  // 打开抽屉时用 setTimeout 异步聚焦关闭按钮；若在它触发前就关闭了抽屉，
  // 这个待执行的回调会把焦点抢回已隐藏的抽屉里，故需在 closeDrawer 中取消。
  var openFocusTimer = null;

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
    报名未开始: "badge-status-closed",
    报名结束: "badge-status-closed",
    已结束: "badge-status-ended",
    已停办: "badge-status-ended",
  };

  var TIER_RANK = { A: 0, B: 1, C: 2, C2: 3 };

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

  function isNjuptFixed(item) {
    var brand = brandFor(item);
    return !!(brand && brand.njupt_fixed);
  }

  function njuptTier(item) {
    var brand = brandFor(item);
    return (brand && brand.njupt_tier) || "";
  }

  function resolveItemLink(item) {
    var brand = brandFor(item) || {};
    if (
      window.CompStatus &&
      typeof window.CompStatus.resolvePublicLink === "function"
    ) {
      return window.CompStatus.resolvePublicLink(item, brand);
    }
    // 兜底须与 status.js 同严格：预计字段 / 伪参数均拦截
    var brandHomeOnly =
      item.link_kind === "brand_home" ||
      item.schedule_source === "estimated" ||
      (item.id && String(item.id).indexOf("estimate-") === 0) ||
      Boolean(item.registration_start_estimated) ||
      Boolean(item.registration_end_estimated);
    function fakeUrl(url) {
      if (!url || typeof url !== "string") return false;
      var lower = url.toLowerCase();
      return (
        lower.indexOf("estimate=") !== -1 ||
        lower.indexOf("estimated=") !== -1 ||
        lower.indexOf("/estimate/") !== -1 ||
        lower.indexOf("?estimate") !== -1 ||
        lower.indexOf("&estimate") !== -1
      );
    }
    var href = "";
    var label = "赛事主页";
    if (brandHomeOnly) {
      href = brand.official_home || "";
      label = "赛事主页";
    } else if (item.link) {
      href = item.link;
      label = "查看原文";
    } else {
      href = brand.official_home || "";
      label = "赛事主页";
    }
    if (href && fakeUrl(href)) href = "";
    return { href: href, label: label, brandHomeOnly: brandHomeOnly };
  }

  function sourceLink(item) {
    return resolveItemLink(item).href || "";
  }

  function sourceLabel(item) {
    return resolveItemLink(item).label || "赛事主页";
  }

  function formatDate(value) {
    if (!value) return "";
    if (typeof value === "string") return value;
    if (value instanceof Date && !isNaN(value.getTime())) {
      var y = value.getFullYear();
      var m = String(value.getMonth() + 1).padStart
        ? String(value.getMonth() + 1).padStart(2, "0")
        : ("0" + (value.getMonth() + 1)).slice(-2);
      var d = String(value.getDate()).padStart
        ? String(value.getDate()).padStart(2, "0")
        : ("0" + value.getDate()).slice(-2);
      return y + "-" + m + "-" + d;
    }
    return String(value);
  }

  function timeLine(item) {
    if (item.needs_review === true) return "见官网详情";
    var meta = window.CompStatus.computeStatus(item);
    var status = meta.status;
    var schedule = window.CompStatus.resolveRegistrationSchedule
      ? window.CompStatus.resolveRegistrationSchedule(item)
      : {
          start: window.CompStatus.parseDate(item.registration_start),
          end: window.CompStatus.parseDate(item.registration_end),
          estimated: false,
        };
    var prefix = schedule.estimated ? "预计" : "";
    var rs = formatDate(schedule.start || item.registration_start);
    var re = formatDate(schedule.end || item.registration_end);

    if ((status === "即将开始报名" || status === "报名未开始") && rs) {
      if (re) {
        return prefix + "报名开始 " + rs + "，截止 " + re;
      }
      return prefix + "报名开始 " + rs;
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
    if (rs && re) {
      return prefix + "报名 " + rs + " 至 " + re;
    }
    if (re) return prefix + "报名截止 " + re;
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
      _estimated: Boolean(statusMeta.estimated),
      _scheduleSource: statusMeta.scheduleSource || "none",
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
    return window.CompStatus.isInternationalKind
      ? window.CompStatus.isInternationalKind(item)
      : item.kind === "国际赛事";
  }

  /**
   * 主栏（全部 / 全国 / 大厂 / 状态筛选）不展示国际赛事；
   * 国际赛单独芯片；搜索有关键词时仍可命中国际赛事。
   */
  function inMainLane(item) {
    return window.CompStatus.inMainLane
      ? window.CompStatus.inMainLane(item)
      : !isInternational(item);
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
        // 与 CompStatus.matchesStatusChip 同源：有核验在报区间必出现
        if (!window.CompStatus.matchesStatusChip(item, "报名中")) return false;
      } else if (state.quick === "即将开始报名") {
        // 开报前 30 天；国际不进；有核验 registration_start 进入窗口后必出现
        if (!window.CompStatus.matchesStatusChip(item, "即将开始报名")) {
          return false;
        }
      } else if (state.quick === "进行中") {
        if (!window.CompStatus.matchesStatusChip(item, "进行中")) return false;
      } else {
        // 全部：默认主栏不含国际赛；有搜索词时放行国际赛，便于检索
        if (!query && !inMainLane(item)) return false;
      }

      return matchesQuery(item, query);
    });

    list.sort(function (a, b) {
      // 1) 当前机会优先（状态 rank，与 status.js 一致）
      // 2) 同状态下：校认定固定清单优先，再 A>B>C>C2
      // 3) 其余走通用比较（截止日 / 届次 / 名称）
      var aRank =
        a._statusMeta && a._statusMeta.rank != null
          ? a._statusMeta.rank
          : 6;
      var bRank =
        b._statusMeta && b._statusMeta.rank != null
          ? b._statusMeta.rank
          : 6;
      if (aRank !== bRank) return aRank - bRank;

      var aFixed = isNjuptFixed(a) ? 0 : 1;
      var bFixed = isNjuptFixed(b) ? 0 : 1;
      if (aFixed !== bFixed) return aFixed - bFixed;

      var aTier = TIER_RANK[njuptTier(a)];
      var bTier = TIER_RANK[njuptTier(b)];
      if (aTier == null) aTier = 9;
      if (bTier == null) bTier = 9;
      if (aTier !== bTier) return aTier - bTier;

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
          ? "仅显示开报前 30 天内、已核验报名开始日的赛事（国际赛不计入）；有日期进入窗口后会自动出现"
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

      var statusLabel = item._urgent
        ? "即将截止"
        : item._status === "报名未开始"
          ? ""
          : item._status === "待复核"
            ? ""
            : item._status;
      var statusBadge =
        !statusLabel
          ? ""
          : '<span class="' +
            statusClass(item._status, item._urgent) +
            '">' +
            escapeHtml(statusLabel) +
            "</span>";
      var tier = njuptTier(item);
      var tierBadge = tier
        ? '<span class="badge badge-njupt-tier" title="南邮校认定 ' +
          escapeAttr(tier) +
          ' 类">校认定' +
          escapeHtml(tier) +
          "</span>"
        : "";
      var estimatedBadge = item._estimated
        ? '<span class="badge badge-estimated" title="报名日据往年推算，以官网为准">预计</span>'
        : "";
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
        tierBadge +
        estimatedBadge +
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
    var drawerStatus =
      enriched._urgent
        ? "即将截止"
        : enriched._status === "待复核" || enriched._status === "报名未开始"
          ? ""
          : enriched._status;
    var statusSection = drawerStatus
      ? '<div class="drawer-section"><strong>状态</strong>' +
        escapeHtml(drawerStatus) +
        "</div>"
      : "";
    var tier = njuptTier(item);
    var tierSection = tier
      ? '<div class="drawer-section"><strong>校认定</strong>' +
        escapeHtml(tier) +
        " 类（南邮创新创业竞赛项目认定目录）</div>"
      : "";
    var estimateSection = enriched._estimated
      ? '<div class="drawer-notice">报名日为据往年推算的<strong>预计</strong>时间，不构成官方通知。' +
        "下方按钮仅打开赛事<strong>品牌官网</strong>，不是本届报名页；请以官网与校内通知为准。" +
        (item.estimate_note
          ? " " + escapeHtml(item.estimate_note)
          : "") +
        "</div>"
      : "";
    lastFocused = trigger || document.activeElement;

    $("drawer-title").textContent = item.name;
    $("drawer-body").innerHTML =
      '<div class="drawer-section"><strong>类型</strong>' +
      escapeHtml(item.kind) +
      "</div>" +
      tierSection +
      statusSection +
      estimateSection +
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
    openFocusTimer = window.setTimeout(function () {
      openFocusTimer = null;
      $("drawer-close").focus();
    }, 0);
  }

  function closeDrawer() {
    if (!$("drawer").classList.contains("is-open")) return;
    // 先撤销尚未执行的「聚焦关闭按钮」，否则它会在恢复焦点之后再抢一次，
    // 把键盘用户留在已隐藏的抽屉上（快速按 Esc 时必现）。
    if (openFocusTimer !== null) {
      window.clearTimeout(openFocusTimer);
      openFocusTimer = null;
    }
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
