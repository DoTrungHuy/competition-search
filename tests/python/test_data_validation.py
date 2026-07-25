# -*- coding: utf-8 -*-
from __future__ import print_function

import datetime
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import link_health
import validate_data


class ProductionDataTests(unittest.TestCase):
    def test_production_data_passes_validator(self):
        errors, warnings = validate_data.validate()
        self.assertEqual(errors, [])
        self.assertTrue(any("needs_review" in warning for warning in warnings))


class OverrideExpiryTests(unittest.TestCase):
    """动态 status_override 必须能判断新鲜度，否则会永久谎报「现在能报名」。"""

    def test_expiry_falls_back_to_last_checked_plus_window(self):
        self.assertEqual(
            validate_data.override_expiry({"last_checked": "2026-07-24"}),
            datetime.date(2026, 10, 22),
        )

    def test_explicit_until_takes_precedence(self):
        self.assertEqual(
            validate_data.override_expiry(
                {"last_checked": "2026-07-24", "status_override_until": "2026-08-31"}
            ),
            datetime.date(2026, 8, 31),
        )

    def test_expiry_is_unknown_without_any_freshness_signal(self):
        self.assertIsNone(validate_data.override_expiry({}))

    def test_stale_active_override_warns_but_never_errors(self):
        """过期只告警：前端已能自愈，不该让无人值守的周更流水线整体中断。"""
        errors, warnings = validate_data.validate(today=datetime.date(2199, 1, 1))
        self.assertEqual(errors, [])
        self.assertTrue(
            any("status_override" in warning and "过期" in warning for warning in warnings)
        )

    def test_fresh_override_produces_no_expiry_warning(self):
        errors, warnings = validate_data.validate(today=datetime.date(2026, 7, 25))
        self.assertEqual(errors, [])
        self.assertFalse(any("已于" in warning for warning in warnings))

    def test_terminal_override_never_expires(self):
        for override in ("已结束", "已停办", "报名结束"):
            self.assertIn(override, validate_data.TERMINAL_STATUS_OVERRIDES)
            self.assertIn(override, validate_data.STATUS_OVERRIDES)


class LinkStatusValidationTests(unittest.TestCase):
    """link_status / degraded 字段与 3% 预算门禁。"""

    def test_budget_helper_over_cap(self):
        # floor(1*0.03)=0; one degraded is over cap
        comps = [{"id": "a", "link_status": "degraded"}]
        errors = link_health.budget_errors(comps)
        self.assertEqual(len(errors), 1)
        self.assertIn("超预算", errors[0])

    def test_budget_helper_under_cap(self):
        # floor(34*0.03)=1
        comps = [{"id": "n%02d" % i} for i in range(33)]
        comps.append({"id": "d", "link_status": "degraded"})
        self.assertEqual(link_health.budget_errors(comps), [])

    def test_degraded_requires_reason_and_date(self):
        errors = link_health.degraded_field_errors(
            {"id": "x", "link_status": "degraded"}, prefix="c[0]"
        )
        self.assertTrue(any("reason" in e for e in errors))
        self.assertTrue(any("checked_at" in e for e in errors))

    def test_degraded_with_reason_and_date_ok(self):
        errors = link_health.degraded_field_errors(
            {
                "id": "x",
                "link_status": "degraded",
                "link_status_reason": "timeout",
                "link_status_checked_at": "2026-07-25",
            },
            prefix="c[0]",
        )
        self.assertEqual(errors, [])

    def test_ok_or_missing_link_status_no_field_errors(self):
        self.assertEqual(link_health.degraded_field_errors({"id": "a"}), [])
        self.assertEqual(
            link_health.degraded_field_errors(
                {"id": "b", "link_status": "ok"}
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()

