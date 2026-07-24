"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const visits = require("../../js/visits.js");

test("every page load uses one fixed increment endpoint", () => {
  assert.equal(
    visits.counterUrl(),
    "https://api.counterapi.dev/v1/competition-search/pageviews/up"
  );
});

test("counter responses are normalized without inventing a local value", () => {
  assert.equal(visits.extractCount({ value: 12 }), 12);
  assert.equal(visits.extractCount({ count: 13 }), 13);
  assert.equal(visits.extractCount({ data: { up_count: 14 } }), 14);
  assert.equal(visits.extractCount({ unexpected: true }), null);
});
