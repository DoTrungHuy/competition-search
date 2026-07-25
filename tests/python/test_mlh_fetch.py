# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import fetch_mlh as mlh


# 取自 mlh.com 赛季页的真实结构：React 服务端渲染，属性是驼峰 itemProp，
# 且赛事下嵌套 Place/PostalAddress 子作用域（内含同名 itemprop 干扰项）。
SEASON_HTML = """
<div>
  <a itemscope="" itemtype="https://schema.org/Event"
     href="https://hexafalls.org/?utm_source=mlh&utm_campaign=events&utm_content=Hexafalls+2">
    <meta itemProp="url" content="https://hexafalls.org"/>
    <meta itemProp="startDate" content="2026-07-24T15:01:00Z"/>
    <meta itemProp="endDate" content="2026-07-26T21:00:00Z"/>
    <div itemProp="location" itemScope="" itemType="https://schema.org/Place">
      <span itemProp="name">Agarpara Kolkata, West Bengal</span>
      <div itemProp="address" itemScope="" itemType="https://schema.org/PostalAddress">
        <meta itemProp="startDate" content="1999-01-01T00:00:00Z"/>
      </div>
    </div>
  </a>
  <a itemscope="" itemtype="https://schema.org/Event"
     href="https://nodates.example/?utm_campaign=events&utm_content=No+Dates+Event"></a>
  <a href="https://unrelated.example/?utm_campaign=newsletter&utm_content=Ignore+Me"></a>
</div>
"""


class MlhParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = mlh.parse_events(SEASON_HTML)

    def test_only_event_links_are_collected(self):
        self.assertEqual(
            sorted(self.events), ["https://hexafalls.org/", "https://nodates.example/"]
        )

    def test_name_comes_from_utm_content(self):
        self.assertEqual(self.events["https://hexafalls.org/"]["name"], "Hexafalls 2")

    def test_schedule_is_read_from_microdata(self):
        event = self.events["https://hexafalls.org/"]
        self.assertEqual(event["competition_start"], "2026-07-24")
        self.assertEqual(event["competition_end"], "2026-07-26")

    def test_nested_place_scope_does_not_leak_dates(self):
        """嵌套 PostalAddress 里的同名 itemprop 不得被当成赛事日期。"""
        self.assertNotEqual(
            self.events["https://hexafalls.org/"]["competition_start"], "1999-01-01"
        )

    def test_event_without_dates_stays_dateless(self):
        event = self.events["https://nodates.example/"]
        self.assertIsNone(event["competition_start"])
        self.assertIsNone(event["competition_end"])


class MlhDraftRecordTests(unittest.TestCase):
    def test_dates_are_written_for_source_schedule_pickup(self):
        events = mlh.parse_events(SEASON_HTML)
        record = mlh.to_draft_record(
            events["https://hexafalls.org/"], "https://hexafalls.org/", "2027"
        )
        self.assertEqual(record["competition_start"], "2026-07-24")
        self.assertEqual(record["competition_end"], "2026-07-26")
        # 草稿阶段一律待复核；是否转正由 apply_reviewed 的 can_auto_verify 决定。
        self.assertTrue(record["needs_review"])
        self.assertIsNone(record["last_checked"])

    def test_dateless_event_does_not_get_empty_schedule_fields(self):
        events = mlh.parse_events(SEASON_HTML)
        record = mlh.to_draft_record(
            events["https://nodates.example/"], "https://nodates.example/", "2027"
        )
        self.assertNotIn("competition_start", record)
        self.assertNotIn("competition_end", record)

    def test_source_schedule_is_recognized_by_pipeline(self):
        """草稿里的日期必须能被审核阶段当作「源日期」采信，否则改了也白改。"""
        from schedule_utils import has_usable_schedule, schedule_from_source_record

        events = mlh.parse_events(SEASON_HTML)
        record = mlh.to_draft_record(
            events["https://hexafalls.org/"], "https://hexafalls.org/", "2027"
        )
        schedule = schedule_from_source_record(record)
        self.assertTrue(has_usable_schedule(schedule))
        self.assertEqual(schedule["schedule_source"], "source")
        self.assertEqual(schedule["competition_start"], "2026-07-24")


class IsoDateTests(unittest.TestCase):
    def test_utc_timestamp_is_reduced_to_date(self):
        self.assertEqual(mlh.iso_date("2026-07-24T15:01:00Z"), "2026-07-24")

    def test_plain_date_passes_through(self):
        self.assertEqual(mlh.iso_date("2026-07-24"), "2026-07-24")

    def test_impossible_and_malformed_values_are_dropped(self):
        for value in ("2026-13-45T00:00:00Z", "2026-02-30", "garbage", "", None):
            self.assertIsNone(mlh.iso_date(value))


if __name__ == "__main__":
    unittest.main()
