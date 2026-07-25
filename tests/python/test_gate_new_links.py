# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import gate_new_links


class FakeResponse(object):
    def __init__(self, code):
        self.status_code = code
        self.url = "https://example.com"
        self.history = []

    def close(self):
        pass


class GateTests(unittest.TestCase):
    def test_drop_404_links(self):
        def fake_get(url, **kwargs):
            if "gone" in url:
                return FakeResponse(404)
            return FakeResponse(200)

        records = [
            {"id": "a", "link": "https://example.com/ok"},
            {"id": "b", "link": "https://example.com/gone"},
        ]
        out, dropped = gate_new_links.filter_broken_links(records, get=fake_get)
        self.assertEqual(out[0].get("link"), "https://example.com/ok")
        self.assertFalse(out[1].get("link"))
        self.assertEqual(len(dropped), 1)
        self.assertEqual(dropped[0]["id"], "b")

    def test_keep_403(self):
        def fake_get(url, **kwargs):
            return FakeResponse(403)

        records = [{"id": "a", "link": "https://example.com/bot"}]
        out, dropped = gate_new_links.filter_broken_links(records, get=fake_get)
        self.assertEqual(out[0]["link"], "https://example.com/bot")
        self.assertEqual(dropped, [])

    def test_drop_410_and_demote_verified(self):
        def fake_get(url, **kwargs):
            return FakeResponse(410)

        records = [
            {
                "id": "c",
                "link": "https://example.com/gone",
                "needs_review": False,
                "last_checked": "2026-07-25",
                "registration_start": "2026-07-01",
                "registration_end": "2026-07-31",
                "competition_start": "2026-08-01",
                "competition_end": "2026-08-02",
            }
        ]
        out, dropped = gate_new_links.filter_broken_links(records, get=fake_get)
        self.assertEqual(len(dropped), 1)
        item = out[0]
        self.assertFalse(item.get("link"))
        self.assertTrue(item["needs_review"])
        self.assertIsNone(item["last_checked"])
        self.assertNotIn("registration_start", item)
        self.assertNotIn("registration_end", item)
        self.assertNotIn("competition_start", item)
        self.assertNotIn("competition_end", item)

    def test_keep_network_errors(self):
        def fake_get(url, **kwargs):
            raise gate_new_links.requests.exceptions.Timeout("slow")

        records = [{"id": "a", "link": "https://example.com/timeout"}]
        out, dropped = gate_new_links.filter_broken_links(records, get=fake_get)
        self.assertEqual(out[0]["link"], "https://example.com/timeout")
        self.assertEqual(dropped, [])


if __name__ == "__main__":
    unittest.main()
