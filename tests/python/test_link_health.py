# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import link_health


class BudgetTests(unittest.TestCase):
    def test_max_allowed_floor_3_percent(self):
        self.assertEqual(link_health.max_degraded_allowed(0), 0)
        self.assertEqual(link_health.max_degraded_allowed(1), 0)
        self.assertEqual(link_health.max_degraded_allowed(33), 0)
        self.assertEqual(link_health.max_degraded_allowed(34), 1)
        self.assertEqual(link_health.max_degraded_allowed(203), 6)

    def test_count_degraded(self):
        comps = [
            {"id": "a", "link_status": "degraded"},
            {"id": "b"},
            {"id": "c", "link_status": "ok"},
            {"id": "d", "link_status": "degraded"},
        ]
        self.assertEqual(link_health.count_degraded(comps), 2)


class EnforceTests(unittest.TestCase):
    def test_under_budget_unchanged(self):
        comps = [
            {
                "id": "keep",
                "link_status": "degraded",
                "link_status_reason": "x",
                "link_status_checked_at": "2026-07-25",
                "has_campus_notice": True,
            }
        ]
        out, dropped = link_health.enforce_degraded_budget(comps)
        self.assertEqual(dropped, [])
        self.assertEqual(out[0]["link_status"], "degraded")

    def test_over_budget_keeps_higher_priority_and_clears_rest(self):
        # max_allowed for 100 items = 3
        comps = []
        for i in range(97):
            comps.append({"id": "n%02d" % i, "has_campus_notice": False})
        # 4 degraded; only 3 allowed
        comps.append(
            {
                "id": "campus-high",
                "link_status": "degraded",
                "link_status_reason": "bad",
                "link_status_checked_at": "2026-07-25",
                "has_campus_notice": True,
                "link": "https://example.com/dead",
                "kind": "全国赛事",
            }
        )
        comps.append(
            {
                "id": "mlh-low",
                "link_status": "degraded",
                "link_status_reason": "bad",
                "link_status_checked_at": "2026-07-25",
                "has_campus_notice": False,
                "link": "https://example.com/mlh-dead",
                "kind": "国际赛事",
                "brand_id": "mlh",
            }
        )
        comps.append(
            {
                "id": "domestic-mid",
                "link_status": "degraded",
                "link_status_reason": "bad",
                "link_status_checked_at": "2026-07-25",
                "has_campus_notice": False,
                "link": "https://example.com/dom-dead",
                "kind": "全国赛事",
            }
        )
        comps.append(
            {
                "id": "another-low",
                "link_status": "degraded",
                "link_status_reason": "bad",
                "link_status_checked_at": "2026-07-25",
                "has_campus_notice": False,
                "link": "https://example.com/x",
                "kind": "国际赛事",
                "brand_id": "devpost",
            }
        )
        out, dropped = link_health.enforce_degraded_budget(comps)
        degraded_ids = [c["id"] for c in out if c.get("link_status") == "degraded"]
        self.assertEqual(len(degraded_ids), 3)
        self.assertIn("campus-high", degraded_ids)
        self.assertNotIn("mlh-low", degraded_ids)  # 国际低优先应被挤掉之一
        # 被挤掉的应清除字段并清空 link
        mlh = next(c for c in out if c["id"] == "mlh-low")
        self.assertIsNone(mlh.get("link_status"))
        self.assertFalse(mlh.get("link"))
        self.assertTrue(any(d["id"] == "mlh-low" for d in dropped))

    def test_validate_degraded_fields_helper(self):
        errors = link_health.degraded_field_errors(
            {"id": "x", "link_status": "degraded"}, prefix="c[0]"
        )
        self.assertTrue(any("reason" in e for e in errors))
        self.assertTrue(any("checked_at" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
