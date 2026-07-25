# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import apply_reviewed
import schedule_utils


def _passthrough_gate(records, timeout=15, get=None):
    """测试默认不打真网：保留 link。"""
    return records, []


class ScheduleUtilsTests(unittest.TestCase):
    def test_parse_devpost_range(self):
        start, end = schedule_utils.parse_english_range("Jul 01 - Jul 31, 2026")
        self.assertEqual(start, "2026-07-01")
        self.assertEqual(end, "2026-07-31")

    def test_source_schedule_from_text(self):
        record = {
            "source_schedule_text": "Jul 01 - Jul 31, 2026",
            "source_list": "devpost",
        }
        schedule = schedule_utils.schedule_from_source_record(record)
        self.assertEqual(schedule["registration_start"], "2026-07-01")
        self.assertEqual(schedule["registration_end"], "2026-07-31")
        self.assertEqual(schedule["schedule_source"], "source")

    def test_kaggle_deadline(self):
        record = {"deadline": "2026-08-15T23:59:00Z", "source_list": "kaggle"}
        schedule = schedule_utils.schedule_from_source_record(record)
        self.assertEqual(schedule["registration_end"], "2026-08-15")
        self.assertEqual(schedule["competition_end"], "2026-08-15")

    def test_can_auto_verify_requires_link_and_date(self):
        schedule = {
            "registration_end": "2026-08-01",
            "registration_start": None,
            "competition_start": None,
            "competition_end": None,
        }
        self.assertFalse(schedule_utils.can_auto_verify(None, schedule))
        self.assertTrue(
            schedule_utils.can_auto_verify("https://example.com/event", schedule)
        )


class ApplyReviewedTests(unittest.TestCase):
    def test_verified_when_schedule_present(self):
        reviewed = {
            "accepted": [
                {
                    "record": {
                        "id": "test-1",
                        "edition": "2026",
                        "track_id": "t1",
                        "name": "Test Hack",
                        "kind": "国际赛事",
                        "info_channel": "官方渠道",
                        "eligibility": "open",
                        "link": "https://example.com/hack",
                    },
                    "decision": {
                        "verdict": "accept",
                        "kind": "国际赛事",
                        "brand_id": "devpost",
                        "new_brand": None,
                        "registration_start": "2026-07-01",
                        "registration_end": "2026-07-31",
                        "competition_start": None,
                        "competition_end": None,
                        "schedule_source": "source",
                        "schedule_confidence": "high",
                    },
                }
            ]
        }
        competitions_doc = {"meta": {"schema_version": 3}, "competitions": []}
        brands_doc = {
            "brands": [
                {
                    "brand_id": "devpost",
                    "name": "Devpost",
                    "kind": "国际赛事",
                    "official_home": "https://devpost.com/hackathons",
                }
            ]
        }
        with mock.patch("apply_reviewed.filter_broken_links", side_effect=_passthrough_gate):
            added, created, skipped, verified, pending = apply_reviewed.apply(
                reviewed, competitions_doc, brands_doc
            )
        self.assertEqual(len(added), 1)
        self.assertEqual(verified, 1)
        self.assertEqual(pending, 0)
        self.assertEqual(skipped, [])
        item = competitions_doc["competitions"][0]
        self.assertFalse(item["needs_review"])
        self.assertEqual(item["registration_end"], "2026-07-31")
        self.assertTrue(item.get("last_checked"))

    def test_pending_when_no_schedule(self):
        reviewed = {
            "accepted": [
                {
                    "record": {
                        "id": "test-2",
                        "edition": "2026",
                        "track_id": "t2",
                        "name": "No Dates",
                        "kind": "国际赛事",
                        "info_channel": "官方渠道",
                        "eligibility": "open",
                        "link": "https://example.com/nodates",
                    },
                    "decision": {
                        "verdict": "accept",
                        "kind": "国际赛事",
                        "brand_id": "mlh",
                        "new_brand": None,
                        "registration_start": None,
                        "registration_end": None,
                        "competition_start": None,
                        "competition_end": None,
                        "schedule_source": None,
                        "schedule_confidence": None,
                    },
                }
            ]
        }
        competitions_doc = {"meta": {"schema_version": 3}, "competitions": []}
        brands_doc = {
            "brands": [
                {
                    "brand_id": "mlh",
                    "name": "MLH",
                    "kind": "国际赛事",
                    "official_home": "https://mlh.io",
                }
            ]
        }
        with mock.patch("apply_reviewed.filter_broken_links", side_effect=_passthrough_gate):
            added, created, skipped, verified, pending = apply_reviewed.apply(
                reviewed, competitions_doc, brands_doc
            )
        self.assertEqual(verified, 0)
        self.assertEqual(pending, 1)
        item = competitions_doc["competitions"][0]
        self.assertTrue(item["needs_review"])
        self.assertIsNone(item.get("registration_end"))
        self.assertIsNone(item.get("last_checked"))

    def test_broken_link_demotes_before_append(self):
        reviewed = {
            "accepted": [
                {
                    "record": {
                        "id": "test-3",
                        "edition": "2026",
                        "track_id": "t3",
                        "name": "Dead Link Hack",
                        "kind": "国际赛事",
                        "info_channel": "官方渠道",
                        "eligibility": "open",
                        "link": "https://example.com/gone",
                    },
                    "decision": {
                        "verdict": "accept",
                        "kind": "国际赛事",
                        "brand_id": "devpost",
                        "new_brand": None,
                        "registration_start": "2026-07-01",
                        "registration_end": "2026-07-31",
                        "competition_start": None,
                        "competition_end": None,
                        "schedule_source": "source",
                        "schedule_confidence": "high",
                    },
                }
            ]
        }
        competitions_doc = {"meta": {"schema_version": 3}, "competitions": []}
        brands_doc = {
            "brands": [
                {
                    "brand_id": "devpost",
                    "name": "Devpost",
                    "kind": "国际赛事",
                    "official_home": "https://devpost.com/hackathons",
                }
            ]
        }

        def fake_filter(records, timeout=15, get=None):
            for item in records or []:
                if item.get("link"):
                    item.pop("link", None)
                    if item.get("needs_review") is False:
                        item["needs_review"] = True
                        item["last_checked"] = None
                        for field in (
                            "registration_start",
                            "registration_end",
                            "competition_start",
                            "competition_end",
                        ):
                            item.pop(field, None)
            return records, [{"id": "test-3"}]

        with mock.patch("apply_reviewed.filter_broken_links", side_effect=fake_filter):
            added, created, skipped, verified, pending = apply_reviewed.apply(
                reviewed, competitions_doc, brands_doc
            )
        self.assertEqual(verified, 0)
        self.assertEqual(pending, 1)
        item = competitions_doc["competitions"][0]
        self.assertTrue(item["needs_review"])
        self.assertFalse(item.get("link"))
        self.assertIsNone(item.get("registration_end"))
        self.assertIsNone(item.get("last_checked"))


if __name__ == "__main__":
    unittest.main()
