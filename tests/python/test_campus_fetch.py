# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import fetch_campus_cxcy as campus
from source_config import load_sources


class CampusParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_sources()
        fixture = os.path.join(ROOT, "tests", "fixtures", "njupt_tzgg_sample.html")
        with open(fixture, "rb") as handle:
            cls.html = handle.read()

    def test_parser_uses_full_title_attribute(self):
        items = campus.parse_list_html(
            self.html,
            self.sources["campus"]["base"],
            self.sources["campus"]["selectors"],
        )
        self.assertGreater(len(items), 10)
        self.assertEqual(
            items[0]["title"],
            "【校赛成绩公示】2026年全国大学生物理实验竞赛(创新)校内选拔赛获奖名单",
        )
        self.assertNotIn("...", items[0]["title"])
        self.assertTrue(items[0]["url"].endswith("/page.htm"))

    def test_results_and_funds_are_rejected(self):
        config = self.sources["campus"]
        accepted, reason = campus.classify_title(
            "【校赛成绩公示】2026年竞赛获奖名单",
            config["title_include_any"],
            config["title_exclude_any"],
        )
        self.assertFalse(accepted)
        self.assertIn("排除词", reason)

        accepted, reason = campus.classify_title(
            "关于遴选南邮-紫金科创学生创业基金项目",
            config["title_include_any"],
            config["title_exclude_any"],
        )
        self.assertFalse(accepted)
        self.assertIn("基金", reason)

    def test_competition_notice_is_accepted(self):
        config = self.sources["campus"]
        accepted, _ = campus.classify_title(
            "关于举办2026年全国大学生物联网设计竞赛校内选拔赛的通知",
            config["title_include_any"],
            config["title_exclude_any"],
        )
        self.assertTrue(accepted)

    def test_structure_change_fails_explicitly(self):
        with self.assertRaisesRegex(campus.ParseError, "页面结构可能已变化"):
            campus.parse_list_html(
                b"<html><body><p>layout changed</p></body></html>",
                self.sources["campus"]["base"],
                self.sources["campus"]["selectors"],
            )

    def test_stable_id_is_deterministic(self):
        url = "https://cxcy.njupt.edu.cn/2026/0506/c11336a301334/page.htm"
        first = campus.stable_id(url, "2026-05-06")
        second = campus.stable_id(url, "2026-05-06")
        other = campus.stable_id(url + "?v=2", "2026-05-06")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)

    def test_categorize_separates_new_changed_and_duplicate(self):
        production = [
            {
                "id": "same-id",
                "name": "旧标题",
                "published_at": "2026-05-01",
                "link": "https://example.edu/a/page.htm",
            },
            {
                "id": "duplicate-id",
                "name": "相同标题",
                "published_at": "2026-05-02",
                "link": "https://example.edu/b/page.htm",
            },
        ]
        records = [
            {
                "id": "same-id",
                "name": "新标题",
                "published_at": "2026-05-01",
                "link": "https://example.edu/a/page.htm",
            },
            {
                "id": "duplicate-id",
                "name": "相同标题",
                "published_at": "2026-05-02",
                "link": "https://example.edu/b/page.htm",
            },
            {
                "id": "new-id",
                "name": "新增竞赛",
                "published_at": "2026-05-03",
                "link": "https://example.edu/c/page.htm",
            },
        ]
        result = campus.categorize(records, [], production)
        self.assertEqual(len(result["changed"]), 1)
        self.assertEqual(len(result["duplicate"]), 1)
        self.assertEqual(len(result["new"]), 1)


if __name__ == "__main__":
    unittest.main()
