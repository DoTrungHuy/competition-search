/**
 * 赛事状态、自然年窗口和默认排序。
 *
 * 所有函数都允许传入 today，便于使用固定日期做确定性测试。
 */
(function (global) {
  "use strict";

  var STATUS_RANK = {
    报名中: 1,
    即将开始报名: 2,
    即将开始: 2,
    进行中: 2,
    报名未开始: 3,
    报名结束: 3,
    已结束: 4,
    已停办: 5,
    待复核: 6,
  };

  /** 「即将开始报名」仅在开报前 30 天窗口内（不含开报当天）。 */
  var UPCOMING_REGISTRATION_DAYS = 30;

  /**
   * 终态覆盖：稳定事实，长期有效，不设过期。
   * 其余（报名中/即将开始报名/即将开始/进行中）属动态状态，必须有有效期，
   * 否则一条旧的人工覆盖会永久谎报「现在能报名」。
   */
  var TERMINAL_OVERRIDES = {
    已结束: true,
    已停办: true,
    报名结束: true,
  };

  /** 动态状态覆盖在缺少显式 status_override_until 时，自 last_checked 起的最长有效天数。 */
  var STATUS_OVERRIDE_MAX_DAYS = 90;

  function parseDate(value) {
    if (!value || typeof value !== "string") return null;
    var match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
    if (!match) return null;
    var year = Number(match[1]);
    var month = Number(match[2]);
    var day = Number(match[3]);
    var date = new Date(year, month - 1, day);
    if (
      date.getFullYear() !== year ||
      date.getMonth() !== month - 1 ||
      date.getDate() !== day
    ) {
      return null;
    }
    return date;
  }

  function startOfToday(now) {
    var date = now instanceof Date ? now : new Date();
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  function daysBetween(from, to) {
    return Math.round((to - from) / 86400000);
  }

  /** 覆盖状态的有效截止日：显式 status_override_until 优先，否则 last_checked + 90 天。 */
  function overrideExpiry(item) {
    var explicit = parseDate(item.status_override_until);
    if (explicit) return explicit;
    var checked = parseDate(item.last_checked);
    if (!checked) return null;
    return new Date(
      checked.getFullYear(),
      checked.getMonth(),
      checked.getDate() + STATUS_OVERRIDE_MAX_DAYS
    );
  }

  /**
   * 动态状态覆盖是否已过期。终态覆盖永不过期。
   * 动态覆盖若既无 status_override_until 也无 last_checked，则无从判断新鲜度，
   * 按过期处理——宁可回落到日期推导或「待复核」，也不长期谎报。
   */
  function overrideExpired(item, today) {
    if (TERMINAL_OVERRIDES[item.status_override]) return false;
    var until = overrideExpiry(item);
    if (!until) return true;
    return startOfToday(today) > until;
  }

  /** 两年窗口锚点：结束日 > 截止日 > 开始日 > 发布日。 */
  function anchorDate(item) {
    return (
      parseDate(item.competition_end) ||
      parseDate(item.registration_end) ||
      parseDate(item.competition_start) ||
      parseDate(item.registration_start) ||
      parseDate(item.published_at) ||
      null
    );
  }

  function calendarYearCutoff(today) {
    var current = startOfToday(today);
    var targetYear = current.getFullYear() - 2;
    var targetMonth = current.getMonth();
    var lastDayOfMonth = new Date(targetYear, targetMonth + 1, 0).getDate();
    return new Date(
      targetYear,
      targetMonth,
      Math.min(current.getDate(), lastDayOfMonth)
    );
  }

  function withinTwoYears(item, today) {
    var anchor = anchorDate(item);
    if (!anchor) return true;
    return anchor >= calendarYearCutoff(today);
  }

  function statusResult(status, urgent, nextDate, extra) {
    var result = {
      status: status,
      urgent: Boolean(urgent),
      nextDate: nextDate || null,
      rank: urgent ? 0 : STATUS_RANK[status] == null ? 6 : STATUS_RANK[status],
      scheduleSource: "none",
      estimated: false,
    };
    if (extra) {
      if (extra.scheduleSource) result.scheduleSource = extra.scheduleSource;
      if (extra.estimated) result.estimated = true;
    }
    return result;
  }

  /**
   * 报名日：官方 registration_* 优先；否则可用往年推算字段（固定清单 P1）。
   * 返回 { start, end, source: "official"|"estimated"|"none", estimated: bool }
   */
  function resolveRegistrationSchedule(item) {
    var officialStart = parseDate(item && item.registration_start);
    var officialEnd = parseDate(item && item.registration_end);
    if (officialStart || officialEnd) {
      return {
        start: officialStart,
        end: officialEnd,
        source: "official",
        estimated: false,
      };
    }
    var estStart = parseDate(item && item.registration_start_estimated);
    var estEnd = parseDate(item && item.registration_end_estimated);
    if (estStart || estEnd) {
      return {
        start: estStart,
        end: estEnd,
        source: "estimated",
        estimated: true,
      };
    }
    return { start: null, end: null, source: "none", estimated: false };
  }

  function scheduleMeta(schedule) {
    return {
      scheduleSource: schedule.source,
      estimated: Boolean(schedule.estimated),
    };
  }

  function computeStatus(item, today) {
    var current = startOfToday(today);
    if (item.active === false) return statusResult("已停办", false);
    if (item.needs_review === true) return statusResult("待复核", false);

    var schedule = resolveRegistrationSchedule(item);
    var registrationStart = schedule.start;
    var registrationEnd = schedule.end;
    var competitionStart = parseDate(item.competition_start);
    var competitionEnd = parseDate(item.competition_end);
    var meta = scheduleMeta(schedule);

    // 官方状态覆盖默认优先；但若已写入「下届报名开始日」且处于开报前 30 天窗口，
    // 则不再被过期的「已结束/报名结束」挡住。
    if (item.status_override) {
      var override = String(item.status_override);
      var daysToRegOverride = registrationStart
        ? daysBetween(current, registrationStart)
        : null;
      var upcomingWindow =
        daysToRegOverride != null &&
        daysToRegOverride >= 1 &&
        daysToRegOverride <= UPCOMING_REGISTRATION_DAYS;
      var staleEnded =
        (override === "已结束" || override === "报名结束") && upcomingWindow;
      // 动态覆盖过期后不再 return，落到下方日期推导；无日期时最终为「待复核」。
      if (!staleEnded && !overrideExpired(item, current)) {
        // override 本身视为官方口径，不标预计
        return statusResult(override, false, null, {
          scheduleSource: "official",
          estimated: false,
        });
      }
    }

    // 即将开始报名：today < registration_start 且距开报 1–30 天（开报当天起算报名中）
    if (registrationStart && current < registrationStart) {
      var daysToReg = daysBetween(current, registrationStart);
      if (daysToReg >= 1 && daysToReg <= UPCOMING_REGISTRATION_DAYS) {
        return statusResult("即将开始报名", false, registrationStart, meta);
      }
      // 开报日仍在 30 天之外：不进「即将报名」芯片，也不落成待复核
      return statusResult("报名未开始", false, registrationStart, meta);
    }

    if (registrationEnd && current <= registrationEnd) {
      var registrationOpen = !registrationStart || current >= registrationStart;
      if (registrationOpen) {
        var daysLeft = daysBetween(current, registrationEnd);
        return statusResult(
          "报名中",
          daysLeft >= 0 && daysLeft <= 7,
          registrationEnd,
          meta
        );
      }
    }

    if (competitionStart && current < competitionStart) {
      return statusResult("即将开始", false, competitionStart, {
        scheduleSource: "official",
        estimated: false,
      });
    }

    if (
      competitionStart &&
      current >= competitionStart &&
      (!competitionEnd || current <= competitionEnd)
    ) {
      return statusResult("进行中", false, competitionEnd, {
        scheduleSource: "official",
        estimated: false,
      });
    }

    if (competitionEnd && current > competitionEnd) {
      return statusResult("已结束", false, competitionEnd, {
        scheduleSource: "official",
        estimated: false,
      });
    }

    if (registrationEnd && current > registrationEnd) {
      return statusResult(
        "报名结束",
        false,
        competitionStart || competitionEnd,
        meta
      );
    }

    return statusResult("待复核", false);
  }

  function editionYear(item) {
    var match = /(20\d{2})/.exec(String(item.edition || ""));
    return match ? Number(match[1]) : 0;
  }

  function compareDates(a, b, descending) {
    var aTime = a instanceof Date ? a.getTime() : Number.POSITIVE_INFINITY;
    var bTime = b instanceof Date ? b.getTime() : Number.POSITIVE_INFINITY;
    if (aTime === bTime) return 0;
    if (descending) return aTime > bTime ? -1 : 1;
    return aTime < bTime ? -1 : 1;
  }

  /**
   * 当前机会优先；已结束赛事按最近结束时间倒序；待核验记录按届次倒序。
   */
  function compareCompetitions(a, b, today) {
    var aStatus = a._statusMeta || computeStatus(a, today);
    var bStatus = b._statusMeta || computeStatus(b, today);

    if (aStatus.rank !== bStatus.rank) return aStatus.rank - bStatus.rank;

    if (aStatus.status === "已结束") {
      var ended = compareDates(anchorDate(a), anchorDate(b), true);
      if (ended) return ended;
    } else if (aStatus.status === "待复核") {
      var editionDiff = editionYear(b) - editionYear(a);
      if (editionDiff) return editionDiff;
    } else {
      var upcoming = compareDates(aStatus.nextDate, bStatus.nextDate, false);
      if (upcoming) return upcoming;
    }

    return String(a.name || "").localeCompare(String(b.name || ""), "zh-CN");
  }

  function isInternationalKind(item) {
    return item && item.kind === "国际赛事";
  }

  /**
   * 状态芯片（报名中 / 即将报名 / 进行中）只服务国内主栏。
   * 国际赛仅在「国际赛」芯片或搜索中出现。
   */
  function inMainLane(item) {
    return !isInternationalKind(item);
  }

/**
   * 公开状态芯片契约：有核验日期且状态匹配时必须为 true。
   * chip: "报名中" | "即将开始报名" | "进行中"
   */
  function matchesStatusChip(item, chip, today) {
    if (!item || item.active === false) return false;
    if (!inMainLane(item)) return false;
    if (!withinTwoYears(item, today)) return false;
    var status = computeStatus(item, today).status;
    if (chip === "报名中") return status === "报名中";
    if (chip === "即将开始报名") return status === "即将开始报名";
    if (chip === "进行中") return status === "进行中";
    return false;
  }

  /**
   * 链接诚信：预计/品牌主页类记录不得使用赛事深链或伪参数。
   * 用于前端展示与测试；生产数据由 validate_data + link_integrity 双闸。
   */
  function isBrandHomeOnly(item) {
    if (!item) return false;
    if (item.link_kind === "brand_home") return true;
    if (item.schedule_source === "estimated") return true;
    if (item.id && String(item.id).indexOf("estimate-") === 0) return true;
    if (item.registration_start_estimated || item.registration_end_estimated) {
      return true;
    }
    return false;
  }

  /**
   * 只放行 http/https 外链。
   * 数据侧 validate_data.valid_url 已是硬闸门，这里是纵深防御的第二层：
   * 卡片与抽屉把 href 直接拼进 innerHTML，escapeAttr 挡得住属性逃逸，
   * 但挡不住 javascript: / data: 这类协议本身。
   */
  function hasSafeScheme(url) {
    if (!url || typeof url !== "string") return false;
    // 浏览器解析协议时会忽略前导空白与内嵌控制字符，先剔除再比对
    var cleaned = url.replace(/[\u0000-\u0020]/g, "").toLowerCase();
    return cleaned.indexOf("http://") === 0 || cleaned.indexOf("https://") === 0;
  }

  function urlHasFakeMarkers(url) {
    if (!url || typeof url !== "string") return false;
    var lower = url.toLowerCase();
    if (lower.indexOf("estimate=") !== -1) return true;
    if (lower.indexOf("estimated=") !== -1) return true;
    if (lower.indexOf("/estimate/") !== -1) return true;
    if (lower.indexOf("?estimate") !== -1) return true;
    if (lower.indexOf("&estimate") !== -1) return true;
    return false;
  }

  /**
   * 解析用户应打开的外链与按钮文案。
   * brand: { official_home } 可选。
   * 返回 { href, label, brandHomeOnly, degraded }
   * 若 href 含伪标记则降级为空（宁可不展示，不给假信息）。
   * degraded 供 UI 展示链路不稳提示，不改变 href 解析逻辑。
   */
  function resolvePublicLink(item, brand) {
    brand = brand || {};
    var brandHomeOnly = isBrandHomeOnly(item);
    var href = "";
    var label = "赛事主页";
    if (brandHomeOnly) {
      href = (brand.official_home || "").trim();
      label = "赛事主页";
    } else if (item && item.link) {
      href = String(item.link).trim();
      label = "查看原文";
    } else {
      href = (brand.official_home || "").trim();
      label = "赛事主页";
    }
    if (href && (urlHasFakeMarkers(href) || !hasSafeScheme(href))) {
      href = "";
    }
    return {
      href: href,
      label: label,
      brandHomeOnly: brandHomeOnly,
      degraded: !!(item && item.link_status === "degraded"),
    };
  }

  var api = {
    STATUS_RANK: STATUS_RANK,
    UPCOMING_REGISTRATION_DAYS: UPCOMING_REGISTRATION_DAYS,
    STATUS_OVERRIDE_MAX_DAYS: STATUS_OVERRIDE_MAX_DAYS,
    parseDate: parseDate,
    startOfToday: startOfToday,
    daysBetween: daysBetween,
    overrideExpiry: overrideExpiry,
    overrideExpired: overrideExpired,
    anchorDate: anchorDate,
    calendarYearCutoff: calendarYearCutoff,
    withinTwoYears: withinTwoYears,
    resolveRegistrationSchedule: resolveRegistrationSchedule,
    computeStatus: computeStatus,
    compareCompetitions: compareCompetitions,
    isInternationalKind: isInternationalKind,
    inMainLane: inMainLane,
    matchesStatusChip: matchesStatusChip,
    isBrandHomeOnly: isBrandHomeOnly,
    hasSafeScheme: hasSafeScheme,
    urlHasFakeMarkers: urlHasFakeMarkers,
    resolvePublicLink: resolvePublicLink,
  };

  global.CompStatus = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
