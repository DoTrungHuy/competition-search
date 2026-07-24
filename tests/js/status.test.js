"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const status = require("../../js/status.js");

function date(value) {
  return status.parseDate(value);
}

test("parseDate rejects malformed and impossible dates", () => {
  assert.equal(date("2026-02-30"), null);
  assert.equal(date("2026/02/28"), null);
  assert.equal(date(""), null);
  assert.equal(date("2026-02-28").getFullYear(), 2026);
});

test("two-year window uses a calendar cutoff", () => {
  const today = new Date(2026, 1, 28);
  assert.equal(
    status.withinTwoYears({ competition_end: "2024-02-28" }, today),
    true
  );
  assert.equal(
    status.withinTwoYears({ competition_end: "2024-02-27" }, today),
    false
  );
});

test("leap-day cutoff clamps to the last valid calendar day", () => {
  const leapDay = new Date(2024, 1, 29);
  const cutoff = status.calendarYearCutoff(leapDay);
  assert.equal(cutoff.getFullYear(), 2022);
  assert.equal(cutoff.getMonth(), 1);
  assert.equal(cutoff.getDate(), 28);
  assert.equal(
    status.withinTwoYears({ competition_end: "2022-02-28" }, leapDay),
    true
  );
});

test("needs_review never produces a precise public status", () => {
  const result = status.computeStatus(
    {
      needs_review: true,
      registration_end: "2026-12-31",
      active: true,
    },
    new Date(2026, 6, 24)
  );
  assert.equal(result.status, "待复核");
  assert.equal(result.rank, 6);
});

test("registration urgency is derived from the injected date", () => {
  const result = status.computeStatus(
    {
      needs_review: false,
      registration_start: "2026-07-01",
      registration_end: "2026-07-28",
      active: true,
    },
    new Date(2026, 6, 24)
  );
  assert.equal(result.status, "报名中");
  assert.equal(result.urgent, true);
  assert.equal(result.rank, 0);
});

test("competition stays ongoing after registration closes", () => {
  const result = status.computeStatus(
    {
      needs_review: false,
      registration_end: "2026-07-20",
      competition_start: "2026-06-08",
      competition_end: "2026-07-25",
      active: true,
    },
    new Date(2026, 6, 24)
  );
  assert.equal(result.status, "进行中");
});

test("upcoming, closed and ended states are distinct", () => {
  const today = new Date(2026, 6, 24);
  // 2026-08-01 is 8 days after 2026-07-24 → inside 30-day window
  assert.equal(
    status.computeStatus(
      {
        needs_review: false,
        registration_start: "2026-08-01",
        registration_end: "2026-08-10",
      },
      today
    ).status,
    "即将开始报名"
  );
  assert.equal(
    status.computeStatus(
      {
        needs_review: false,
        registration_end: "2026-07-20",
        competition_start: "2026-08-10",
      },
      today
    ).status,
    "即将开始"
  );
  assert.equal(
    status.computeStatus(
      {
        needs_review: false,
        competition_end: "2026-07-20",
      },
      today
    ).status,
    "已结束"
  );
  assert.equal(
    status.computeStatus(
      {
        needs_review: false,
        registration_end: "2026-07-20",
      },
      today
    ).status,
    "报名结束"
  );
});

test("registration_start beyond 30 days is 报名未开始, not 即将开始报名", () => {
  const today = new Date(2026, 6, 24);
  // 2026-09-01 is 39 days later → outside window
  const far = status.computeStatus(
    {
      needs_review: false,
      active: true,
      registration_start: "2026-09-01",
      registration_end: "2026-09-15",
    },
    today
  );
  assert.equal(far.status, "报名未开始");
  assert.equal(far.rank, 3);

  // boundary: exactly 30 days later still counts as upcoming
  const edge = status.computeStatus(
    {
      needs_review: false,
      active: true,
      registration_start: "2026-08-23",
      registration_end: "2026-09-01",
    },
    today
  );
  assert.equal(edge.status, "即将开始报名");
  assert.equal(status.daysBetween(today, status.parseDate("2026-08-23")), 30);

  // open day itself is 报名中 (not 即将开始报名)
  const openDay = status.computeStatus(
    {
      needs_review: false,
      active: true,
      registration_start: "2026-07-24",
      registration_end: "2026-08-10",
    },
    today
  );
  assert.equal(openDay.status, "报名中");
});

test("future registration_start recovers ended override only inside 30-day window", () => {
  const today = new Date(2026, 6, 24);
  const far = status.computeStatus(
    {
      needs_review: false,
      active: true,
      status_override: "已结束",
      competition_end: "2026-05-01",
      registration_start: "2026-10-20",
      registration_end: "2027-03-11",
    },
    today
  );
  // 2026-10-20 is far beyond 30 days; stale override recovery does not apply
  assert.equal(far.status, "已结束");

  const near = status.computeStatus(
    {
      needs_review: false,
      active: true,
      status_override: "已结束",
      competition_end: "2026-05-01",
      registration_start: "2026-08-10",
      registration_end: "2026-09-01",
    },
    today
  );
  assert.equal(near.status, "即将开始报名");
  assert.equal(near.rank, 2);
});

test("active override still wins when registration has not been renewed", () => {
  const today = new Date(2026, 6, 24);
  assert.equal(
    status.computeStatus(
      {
        needs_review: false,
        status_override: "进行中",
        registration_start: "2026-01-01",
        registration_end: "2026-03-01",
      },
      today
    ).status,
    "进行中"
  );
  assert.equal(
    status.computeStatus(
      {
        needs_review: false,
        status_override: "已结束",
        competition_end: "2026-05-01",
      },
      today
    ).status,
    "已结束"
  );
});

test("default sort puts current opportunities before history and review records", () => {
  const today = new Date(2026, 6, 24);
  const items = [
    {
      name: "待核验",
      edition: "2026",
      needs_review: true,
      active: true,
    },
    {
      name: "较早结束",
      edition: "2025",
      competition_end: "2026-06-01",
      needs_review: false,
      active: true,
    },
    {
      name: "进行中",
      edition: "2026",
      competition_start: "2026-07-01",
      competition_end: "2026-08-01",
      needs_review: false,
      active: true,
    },
    {
      name: "最近结束",
      edition: "2026",
      competition_end: "2026-07-20",
      needs_review: false,
      active: true,
    },
  ];
  items.sort((a, b) => status.compareCompetitions(a, b, today));
  assert.deepEqual(
    items.map((item) => item.name),
    ["进行中", "最近结束", "较早结束", "待核验"]
  );
});

test("status chips surface verified open and upcoming registration dates", () => {
  const today = new Date(2026, 6, 24);

  const openMain = {
    name: "夹具-在报国内",
    kind: "全国赛事",
    needs_review: false,
    active: true,
    registration_start: "2026-07-01",
    registration_end: "2026-07-31",
  };
  assert.equal(status.computeStatus(openMain, today).status, "报名中");
  assert.equal(status.matchesStatusChip(openMain, "报名中", today), true);
  assert.equal(status.matchesStatusChip(openMain, "即将开始报名", today), false);

  const upcomingMain = {
    name: "夹具-即将开报国内",
    kind: "全国赛事",
    needs_review: false,
    active: true,
    registration_start: "2026-08-10",
    registration_end: "2026-08-20",
  };
  assert.equal(status.computeStatus(upcomingMain, today).status, "即将开始报名");
  assert.equal(
    status.matchesStatusChip(upcomingMain, "即将开始报名", today),
    true
  );
  assert.equal(status.matchesStatusChip(upcomingMain, "报名中", today), false);

  const farMain = {
    name: "夹具-开报尚远",
    kind: "全国赛事",
    needs_review: false,
    active: true,
    registration_start: "2026-10-01",
    registration_end: "2026-10-15",
  };
  assert.equal(status.computeStatus(farMain, today).status, "报名未开始");
  assert.equal(status.matchesStatusChip(farMain, "即将开始报名", today), false);

  const reviewBlocked = {
    name: "夹具-待复核有日期",
    kind: "全国赛事",
    needs_review: true,
    active: true,
    registration_start: "2026-08-05",
    registration_end: "2026-08-20",
  };
  assert.equal(status.computeStatus(reviewBlocked, today).status, "待复核");
  assert.equal(
    status.matchesStatusChip(reviewBlocked, "即将开始报名", today),
    false
  );
  assert.equal(status.matchesStatusChip(reviewBlocked, "报名中", today), false);
});

test("status chips never include international events", () => {
  const today = new Date(2026, 6, 24);
  const openIntl = {
    name: "夹具-国际在报",
    kind: "国际赛事",
    needs_review: false,
    active: true,
    registration_start: "2026-07-01",
    registration_end: "2026-07-31",
  };
  assert.equal(status.computeStatus(openIntl, today).status, "报名中");
  assert.equal(status.inMainLane(openIntl), false);
  assert.equal(status.matchesStatusChip(openIntl, "报名中", today), false);
  assert.equal(
    status.matchesStatusChip(openIntl, "即将开始报名", today),
    false
  );

  const upcomingIntl = {
    name: "夹具-国际即将开报",
    kind: "国际赛事",
    needs_review: false,
    active: true,
    registration_start: "2026-08-10",
    registration_end: "2026-08-20",
  };
  assert.equal(
    status.computeStatus(upcomingIntl, today).status,
    "即将开始报名"
  );
  assert.equal(
    status.matchesStatusChip(upcomingIntl, "即将开始报名", today),
    false
  );
});

test("estimated registration can enter chips and is marked estimated", () => {
  const today = new Date(2026, 6, 24);
  const estimatedOpen = {
    name: "夹具-预计在报",
    kind: "全国赛事",
    needs_review: false,
    active: true,
    registration_start_estimated: "2026-07-01",
    registration_end_estimated: "2026-08-15",
    schedule_source: "estimated",
  };
  const openMeta = status.computeStatus(estimatedOpen, today);
  assert.equal(openMeta.status, "报名中");
  assert.equal(openMeta.estimated, true);
  assert.equal(openMeta.scheduleSource, "estimated");
  assert.equal(status.matchesStatusChip(estimatedOpen, "报名中", today), true);

  const estimatedUpcoming = {
    name: "夹具-预计即将开报",
    kind: "全国赛事",
    needs_review: false,
    active: true,
    registration_start_estimated: "2026-08-10",
    registration_end_estimated: "2026-09-01",
    schedule_source: "estimated",
  };
  const upMeta = status.computeStatus(estimatedUpcoming, today);
  assert.equal(upMeta.status, "即将开始报名");
  assert.equal(upMeta.estimated, true);
  assert.equal(
    status.matchesStatusChip(estimatedUpcoming, "即将开始报名", today),
    true
  );
});

test("official registration dates override estimated fields", () => {
  const today = new Date(2026, 6, 24);
  const mixed = {
    name: "夹具-官方覆盖预计",
    kind: "全国赛事",
    needs_review: false,
    active: true,
    registration_start: "2026-07-01",
    registration_end: "2026-07-31",
    registration_start_estimated: "2026-09-01",
    registration_end_estimated: "2026-09-30",
    schedule_source: "estimated",
  };
  const meta = status.computeStatus(mixed, today);
  assert.equal(meta.status, "报名中");
  assert.equal(meta.estimated, false);
  assert.equal(meta.scheduleSource, "official");
  const schedule = status.resolveRegistrationSchedule(mixed);
  assert.equal(schedule.estimated, false);
  assert.equal(schedule.source, "official");
});

test("resolvePublicLink never surfaces fake estimate deep links", () => {
  const brand = { official_home: "http://www.c4best.cn/" };
  const estimated = {
    id: "estimate-c4-2026",
    schedule_source: "estimated",
    link_kind: "brand_home",
    // 即便脏数据误写入 link，前端也必须忽略
    link: "https://aicontest.baidu.com/rules.html?estimate=2026",
  };
  const resolved = status.resolvePublicLink(estimated, brand);
  assert.equal(resolved.brandHomeOnly, true);
  assert.equal(resolved.label, "赛事主页");
  assert.equal(resolved.href, "http://www.c4best.cn/");
  assert.equal(status.urlHasFakeMarkers(resolved.href), false);

  const official = {
    id: "c4-net-2025",
    link: "http://net.c4best.cn/details/entryGuide",
  };
  const off = status.resolvePublicLink(official, brand);
  assert.equal(off.label, "查看原文");
  assert.equal(off.href, "http://net.c4best.cn/details/entryGuide");

  assert.equal(
    status.urlHasFakeMarkers(
      "https://example.com/x?estimate=2027"
    ),
    true
  );
  const poisonedHome = status.resolvePublicLink(
    { link: "https://ok.example/page" },
    { official_home: "https://bad.example/?estimate=1" }
  );
  // 无 item.link 时走 brand home；含伪标记则降级为空
  const onlyFakeHome = status.resolvePublicLink(
    { id: "estimate-x", schedule_source: "estimated", link_kind: "brand_home" },
    { official_home: "https://bad.example/?estimate=1" }
  );
  assert.equal(onlyFakeHome.href, "");
  assert.ok(poisonedHome);
});
