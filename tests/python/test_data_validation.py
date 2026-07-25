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


if __name__ == "__main__":
    unittest.main()

