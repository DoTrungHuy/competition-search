# -*- coding: utf-8 -*-
from __future__ import print_function

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


if __name__ == "__main__":
    unittest.main()

