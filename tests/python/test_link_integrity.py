# -*- coding: utf-8 -*-
"""链接诚信硬门禁：伪报名链 / 预计深链不得进入生产。"""
from __future__ import print_function

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import apply_registration_estimates as apply_est
import link_integrity
import validate_data


class LinkIntegrityUnitTests(unittest.TestCase):
    def test_detects_estimate_query_fake(self):
        self.assertTrue(
            link_integrity.url_has_fake_markers(
                "https://aicontest.baidu.com/rules.html?estimate=2026"
            )
        )
        self.assertTrue(
            link_integrity.url_has_fake_markers(
                "https://example.com/page?foo=1&estimated=1"
            )
        )
        self.assertTrue(
            link_integrity.url_has_fake_markers("https://example.com/estimate/2027")
        )
        self.assertFalse(
            link_integrity.url_has_fake_markers("http://www.c4best.cn/")
        )

    def test_estimate_record_rejects_deep_link(self):
        brand = {"official_home": "http://www.c4best.cn/"}
        bad = {
            "id": "estimate-c4-2026",
            "schedule_source": "estimated",
            "link_kind": "brand_home",
            "link": "https://aicontest.baidu.com/rules.html?estimate=2026",
            "registration_end_estimated": "2026-07-25",
        }
        errors = link_integrity.check_competition_link_honesty(bad, brand)
        self.assertTrue(any("伪参数" in e or "深链接" in e for e in errors))

    def test_honest_estimate_passes(self):
        brand = {"official_home": "http://www.c4best.cn/"}
        good = {
            "id": "estimate-c4-2026",
            "schedule_source": "estimated",
            "link_kind": "brand_home",
            "registration_start_estimated": "2026-07-04",
            "registration_end_estimated": "2026-07-25",
        }
        self.assertEqual(
            link_integrity.check_competition_link_honesty(good, brand), []
        )

    def test_generator_assert_blocks_fake_link_field(self):
        brand = {"official_home": "http://www.c4best.cn/", "name": "C4"}
        poisoned = {
            "id": "estimate-c4-2026",
            "schedule_source": "estimated",
            "link_kind": "brand_home",
            "link": "https://example.com/x?estimate=1",
        }
        with self.assertRaises(RuntimeError):
            apply_est.assert_estimate_record_honest(poisoned, brand)

    def test_estimate_home_only_never_appends_query(self):
        home = apply_est.estimate_home_only(
            {"official_home": "https://dasai.lanqiao.cn/"}
        )
        self.assertEqual(home, "https://dasai.lanqiao.cn")
        self.assertNotIn("estimate", home or "")


class ProductionLinkHonestyTests(unittest.TestCase):
    def test_production_has_no_fake_or_estimate_deep_links(self):
        errors, _warnings = validate_data.validate()
        honesty = [e for e in errors if "伪" in e or "预计" in e or "深链接" in e]
        self.assertEqual(honesty, [], msg="\n".join(honesty))

        comps = validate_data.load_json("competitions.json")["competitions"]
        brands = {
            b["brand_id"]: b
            for b in validate_data.load_json("brands.json")["brands"]
        }
        audit = link_integrity.audit_collections(comps, brands)
        self.assertEqual(audit, [], msg="\n".join(audit))

        for item in comps:
            link = item.get("link") or ""
            self.assertFalse(
                link_integrity.url_has_fake_markers(link),
                msg="生产 link 含伪标记: %s %s" % (item.get("id"), link),
            )
            if link_integrity.is_estimate_record(item):
                self.assertFalse(
                    bool(link),
                    msg="预计记录仍带 link: %s %s" % (item.get("id"), link),
                )
                self.assertEqual(item.get("link_kind"), "brand_home")


if __name__ == "__main__":
    unittest.main()
