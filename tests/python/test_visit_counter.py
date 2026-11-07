# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ECS_DIR = os.path.join(ROOT, "deploy", "ecs")
if ECS_DIR not in sys.path:
    sys.path.insert(0, ECS_DIR)

import visit_counter  # noqa: E402


class VisitCounterTests(unittest.TestCase):
    def test_counter_store_increments_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "visits.db")
            store = visit_counter.CounterStore(db_path, initial=10)
            self.assertEqual(store.current(), 10)
            self.assertEqual(store.increment(), 11)
            self.assertEqual(store.increment(), 12)

            reopened = visit_counter.CounterStore(db_path, initial=0)
            self.assertEqual(reopened.current(), 12)


if __name__ == "__main__":
    unittest.main()
