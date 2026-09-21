# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import os
import sys
import tempfile
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import review_drafts


class ReviewQueueTests(unittest.TestCase):
    def test_merge_candidates_deduplicates_by_id(self):
        old = [{"id": "same", "name": "old", "ai_reason": "keep-me"}]
        fresh = [{"id": "same", "name": "new"}, {"id": "other", "name": "other"}]
        merged = review_drafts.merge_candidates(old, fresh)
        self.assertEqual([item["id"] for item in merged], ["same", "other"])
        self.assertEqual(merged[0]["name"], "new")
        self.assertEqual(merged[0]["ai_reason"], "keep-me")

    def test_disabled_ai_writes_queue_and_empty_review_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft_path = os.path.join(tmp, "draft.json")
            queue_path = os.path.join(tmp, "queue.json")
            output_path = os.path.join(tmp, "reviewed.json")
            with open(draft_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "review": {
                            "new": [
                                {
                                    "id": "demo-1",
                                    "name": "测试竞赛",
                                    "link": "https://example.com/demo",
                                }
                            ],
                            "changed": [],
                        }
                    },
                    handle,
                    ensure_ascii=False,
                )

            argv = [
                "review_drafts.py",
                "--in",
                draft_path,
                "--queue",
                queue_path,
                "--out",
                output_path,
                "--delay",
                "0",
            ]
            with mock.patch.dict(
                os.environ,
                {"AI_REVIEW_ENABLED": "false"},
                clear=False,
            ), mock.patch.object(sys, "argv", argv):
                os.environ.pop("DEEPSEEK_API_KEY", None)
                code = review_drafts.main()

            self.assertEqual(code, 0)
            with open(queue_path, encoding="utf-8") as handle:
                queue = json.load(handle)
            with open(output_path, encoding="utf-8") as handle:
                reviewed = json.load(handle)
            self.assertEqual(queue["meta"]["count"], 1)
            self.assertEqual(reviewed["meta"]["mode"], "disabled")
            self.assertEqual(reviewed["accepted"], [])
            self.assertEqual(reviewed["rejected"], [])

    def test_enabled_ai_keeps_candidate_and_writes_advisory_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft_path = os.path.join(tmp, "draft.json")
            queue_path = os.path.join(tmp, "queue.json")
            output_path = os.path.join(tmp, "reviewed.json")
            record = {
                "id": "demo-2",
                "name": "测试竞赛",
                "link": "https://example.com/demo2",
                "kind": "全国赛事",
            }
            with open(draft_path, "w", encoding="utf-8") as handle:
                json.dump({"review": {"new": [record], "changed": []}}, handle)

            decision = {
                "verdict": "accept",
                "is_competition": True,
                "kind": "全国赛事",
                "brand_id": "lanqiao",
                "new_brand": None,
                "confidence": "high",
                "reason": "测试通过",
                "registration_start": None,
                "registration_end": None,
                "competition_start": None,
                "competition_end": None,
                "schedule_confidence": None,
            }
            reviewer = mock.Mock()
            reviewer.review.return_value = decision
            argv = [
                "review_drafts.py",
                "--in",
                draft_path,
                "--queue",
                queue_path,
                "--out",
                output_path,
                "--delay",
                "0",
            ]
            with mock.patch.dict(
                os.environ,
                {
                    "AI_REVIEW_ENABLED": "true",
                    "DEEPSEEK_API_KEY": "test-key",
                },
                clear=False,
            ), mock.patch.object(sys, "argv", argv), mock.patch(
                "review_drafts.DeepSeekReviewer",
                return_value=reviewer,
            ):
                code = review_drafts.main()

            self.assertEqual(code, 0)
            with open(queue_path, encoding="utf-8") as handle:
                queue = json.load(handle)
            with open(output_path, encoding="utf-8") as handle:
                reviewed = json.load(handle)
            self.assertEqual(queue["meta"]["count"], 1)
            pending = queue["pending"][0]
            self.assertEqual(pending["ai_verdict"], "ACCEPT")
            self.assertEqual(pending["ai_confidence"], "HIGH")
            self.assertEqual(pending["ai_reason"], "测试通过")
            self.assertEqual(pending["ai_model"], review_drafts.DEFAULT_MODEL)
            self.assertTrue(pending["ai_review_fingerprint"])
            self.assertEqual(reviewed["meta"]["mode"], "advisory")
            self.assertEqual(len(reviewed["accepted"]), 1)

    def test_unchanged_candidate_reuses_existing_ai_advice(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue_path = os.path.join(tmp, "queue.json")
            output_path = os.path.join(tmp, "reviewed.json")
            record = {
                "id": "demo-existing",
                "name": "已有建议竞赛",
                "link": "https://example.com/existing",
            }
            record["ai_verdict"] = "ACCEPT"
            record["ai_confidence"] = "HIGH"
            record["ai_reason"] = "已有建议"
            record["ai_review_fingerprint"] = review_drafts.review_fingerprint(record)
            review_drafts.save_queue(queue_path, [record])

            reviewer = mock.Mock()
            argv = [
                "review_drafts.py",
                "--queue",
                queue_path,
                "--out",
                output_path,
                "--delay",
                "0",
            ]
            with mock.patch.dict(
                os.environ,
                {"AI_REVIEW_ENABLED": "true", "DEEPSEEK_API_KEY": "test-key"},
                clear=False,
            ), mock.patch.object(sys, "argv", argv), mock.patch(
                "review_drafts.DeepSeekReviewer",
                return_value=reviewer,
            ):
                code = review_drafts.main()

            self.assertEqual(code, 0)
            reviewer.review.assert_not_called()
            with open(queue_path, encoding="utf-8") as handle:
                queue = json.load(handle)
            self.assertEqual(queue["meta"]["count"], 1)
            self.assertEqual(queue["pending"][0]["ai_reason"], "已有建议")


if __name__ == "__main__":
    unittest.main()
