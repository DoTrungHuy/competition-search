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
    报名结束: 3,
    已结束: 4,
    已停办: 5,
    待复核: 6,
  };

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

  function statusResult(status, urgent, nextDate) {
    return {
      status: status,
      urgent: Boolean(urgent),
      nextDate: nextDate || null,
      rank: urgent ? 0 : STATUS_RANK[status] == null ? 6 : STATUS_RANK[status],
    };
  }

  function computeStatus(item, today) {
    var current = startOfToday(today);
    if (item.active === false) return statusResult("已停办", false);
    if (item.needs_review === true) return statusResult("待复核", false);

    var registrationStart = parseDate(item.registration_start);
    var registrationEnd = parseDate(item.registration_end);
    var competitionStart = parseDate(item.competition_start);
    var competitionEnd = parseDate(item.competition_end);

    // 官方状态覆盖默认优先；但若已写入「下届报名开始日」且尚未到日，
    // 则不再被过期的「已结束/报名结束」挡住（早期「即将开始报名」能力）。
    if (item.status_override) {
      var override = String(item.status_override);
      var staleEnded =
        (override === "已结束" || override === "报名结束") &&
        registrationStart &&
        current < registrationStart;
      if (!staleEnded) {
        return statusResult(override, false);
      }
    }

    if (registrationStart && current < registrationStart) {
      return statusResult("即将开始报名", false, registrationStart);
    }

    if (registrationEnd && current <= registrationEnd) {
      var registrationOpen = !registrationStart || current >= registrationStart;
      if (registrationOpen) {
        var daysLeft = daysBetween(current, registrationEnd);
        return statusResult(
          "报名中",
          daysLeft >= 0 && daysLeft <= 7,
          registrationEnd
        );
      }
    }

    if (competitionStart && current < competitionStart) {
      return statusResult("即将开始", false, competitionStart);
    }

    if (
      competitionStart &&
      current >= competitionStart &&
      (!competitionEnd || current <= competitionEnd)
    ) {
      return statusResult("进行中", false, competitionEnd);
    }

    if (competitionEnd && current > competitionEnd) {
      return statusResult("已结束", false, competitionEnd);
    }

    if (registrationEnd && current > registrationEnd) {
      return statusResult("报名结束", false, competitionStart || competitionEnd);
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

  var api = {
    STATUS_RANK: STATUS_RANK,
    parseDate: parseDate,
    startOfToday: startOfToday,
    anchorDate: anchorDate,
    calendarYearCutoff: calendarYearCutoff,
    withinTwoYears: withinTwoYears,
    computeStatus: computeStatus,
    compareCompetitions: compareCompetitions,
  };

  global.CompStatus = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
