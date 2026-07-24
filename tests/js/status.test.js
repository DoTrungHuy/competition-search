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

test("future registration_start recovers ended override into upcoming registration", () => {
  const today = new Date(2026, 6, 24);
  const result = status.computeStatus(
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
  assert.equal(result.status, "即将开始报名");
  assert.equal(result.rank, 2);
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
