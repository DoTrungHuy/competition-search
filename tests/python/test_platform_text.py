# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import apply_reviewed
import platform_text


class PlatformTextTests(unittest.TestCase):
    def test_mlh_eligibility_includes_event_name(self):
        record = {"name": "HackFoo 2026", "brand_id": "mlh", "edition": "2026"}
        text = platform_text.eligibility_for(record)
        self.assertIn("HackFoo 2026", text)
        self.assertNotEqual(text, "以活动页面为准")

    def test_devpost_includes_organizer_when_present(self):
        record = {
            "name": "Zero to Query",
            "brand_id": "devpost",
            "organizer": "LingoQL",
        }
        text = platform_text.eligibility_for(record)
        self.assertIn("Zero to Query", text)
        self.assertIn("LingoQL", text)

    def test_two_events_not_identical(self):
        a = platform_text.eligibility_for(
            {"name": "Event A", "brand_id": "mlh", "edition": "2026"}
        )
        b = platform_text.eligibility_for(
            {"name": "Event B", "brand_id": "mlh", "edition": "2026"}
        )
        self.assertNotEqual(a, b)

    def test_enrich_rewrites_generic(self):
        record = {
            "name": "Impact Creation",
            "brand_id": "devpost",
            "eligibility": "以活动页面为准",
            "description": "Devpost 平台国际黑客松，报名与规则以活动页面为准。",
        }
        changed = platform_text.enrich_platform_text(record)
        self.assertTrue(changed)
        self.assertIn("Impact Creation", record["eligibility"])
        self.assertIn("Impact Creation", record["description"])
        self.assertFalse(platform_text.is_generic_eligibility(record["eligibility"]))


class ApplyReviewedPlatformTextTests(unittest.TestCase):
    def test_apply_rewrites_generic_platform_eligibility(self):
        reviewed = {
            "accepted": [
                {
                    "record": {
                        "id": "mlh-test-1",
                        "edition": "2026",
                        "track_id": "mlh-hack-alpha",
                        "name": "Hack Alpha",
                        "kind": "国际赛事",
                        "info_channel": "官方渠道",
                        "eligibility": "以活动页面为准",
                        "description": "MLH 认证的国际黑客松，报名与规则以活动页面为准。",
                        "link": "https://example.com/hack-alpha",
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
        added, created, skipped, verified, pending = apply_reviewed.apply(
            reviewed, competitions_doc, brands_doc
        )
        self.assertEqual(len(added), 1)
        self.assertEqual(skipped, [])
        item = competitions_doc["competitions"][0]
        self.assertIn("Hack Alpha", item["eligibility"])
        self.assertNotEqual(item["eligibility"], "以活动页面为准")
        self.assertIn("Hack Alpha", item["description"])


if __name__ == "__main__":
    unittest.main()
