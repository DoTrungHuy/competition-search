# -*- coding: utf-8 -*-
"""自动将 review_queue.json 中 AI 高/中置信度 ACCEPT 的候选合并进 competitions.json。

流程定位：
    review_drafts.py -> data/review_queue.json -> [本脚本] -> data/competitions.json (+ data/brands.json)

规则：
1. 仅自动放行 ai_verdict == "ACCEPT" 且 ai_confidence in ("HIGH", "MEDIUM") 的候选；
2. 已有确定性去重（id / 品牌+届次+赛道 / 深链接已存在）的候选直接从待审队列移除；
3. 无法匹配品牌的候选保留在 review_queue.json 中交由人工后台处理；
4. AI 判定为 REJECT、LOW 置信度或尚未经 AI 审核的候选保留在 review_queue.json 中。
"""
from __future__ import print_function

import argparse
import os
import sys
from unittest import mock

import apply_reviewed
from fetch_campus_cxcy import guess_brand_id
from review_drafts import load_queue, save_queue
from schedule_utils import (
    clean_schedule,
    has_usable_schedule,
    schedule_from_source_record,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DEFAULT_QUEUE = os.path.join(DATA_DIR, "review_queue.json")
DEFAULT_COMPS = os.path.join(DATA_DIR, "competitions.json")
DEFAULT_BRANDS = os.path.join(DATA_DIR, "brands.json")

AUTO_CONFIDENCES = ("HIGH", "MEDIUM")
DUPLICATE_REASONS = ("id 已存在", "品牌/届次/赛道已存在", "深链接已存在")


def resolve_candidate_brand(record):
    brand_id = record.get("ai_brand_id") or record.get("brand_id")
    if not brand_id:
        brand_id = guess_brand_id(record.get("name"))
    if not brand_id and (
        record.get("source_list") in ("campus", "tzgg", "xkjs")
        or record.get("has_campus_notice")
    ):
        brand_id = "njupt_cxcy"
    return brand_id


def resolve_candidate_schedule(record):
    sched = schedule_from_source_record(record)
    if has_usable_schedule(sched):
        return sched
    ai_sched = record.get("ai_schedule")
    if isinstance(ai_sched, dict):
        conf = str(ai_sched.get("schedule_confidence") or "high").strip().lower()
        source = str(ai_sched.get("schedule_source") or "model").strip().lower()
        cleaned = clean_schedule(ai_sched, source, conf)
        if has_usable_schedule(cleaned):
            return cleaned
    return sched


def build_decision_from_queued(record, brands_by_id=None):
    brand_id = resolve_candidate_brand(record)
    kind = record.get("ai_kind") or record.get("kind")
    if kind not in apply_reviewed.KINDS and brands_by_id and brand_id in brands_by_id:
        kind = brands_by_id[brand_id].get("kind")
    sched = resolve_candidate_schedule(record)
    return {
        "verdict": "accept",
        "is_competition": True,
        "kind": kind,
        "brand_id": brand_id,
        "new_brand": record.get("ai_new_brand"),
        "confidence": str(record.get("ai_confidence") or "high").strip().lower(),
        "reason": str(record.get("ai_reason") or "").strip(),
        "registration_start": sched.get("registration_start"),
        "registration_end": sched.get("registration_end"),
        "competition_start": sched.get("competition_start"),
        "competition_end": sched.get("competition_end"),
        "schedule_source": sched.get("schedule_source"),
        "schedule_confidence": sched.get("schedule_confidence"),
    }


def _passthrough_gate(records, timeout=15, get=None):
    return records, []


def main():
    parser = argparse.ArgumentParser(
        description="自动发布 review_queue.json 中 AI 审核通过的竞赛候选"
    )
    parser.add_argument("--queue", default=DEFAULT_QUEUE, help="review_queue.json 路径")
    parser.add_argument("--competitions", default=DEFAULT_COMPS, help="competitions.json 路径")
    parser.add_argument("--brands", default=DEFAULT_BRANDS, help="brands.json 路径")
    parser.add_argument(
        "--skip-link-gate",
        action="store_true",
        help="跳过逐条外链 HTTP 探活（适合批量释放历史积压）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只报告不写文件")
    args = parser.parse_args()

    pending_list = load_queue(args.queue)
    if not pending_list:
        print("待审核队列为空，无需自动发布。")
        return 0

    competitions_doc = apply_reviewed.load_json(args.competitions)
    brands_doc = apply_reviewed.load_json(args.brands)
    brands_by_id = {
        b.get("brand_id"): b for b in brands_doc.get("brands", []) if b.get("brand_id")
    }

    eligible_entries = []
    eligible_records = []
    remaining_queue = []

    for record in pending_list:
        verdict = str(record.get("ai_verdict") or "").strip().upper()
        confidence = str(record.get("ai_confidence") or "").strip().upper()
        if verdict == "ACCEPT" and confidence in AUTO_CONFIDENCES:
            if record.get("kind") not in apply_reviewed.KINDS:
                bid = resolve_candidate_brand(record)
                if bid in brands_by_id:
                    record["kind"] = brands_by_id[bid].get("kind")
            decision = build_decision_from_queued(record, brands_by_id)
            eligible_entries.append({"record": record, "decision": decision})
            eligible_records.append(record)
        else:
            remaining_queue.append(record)

    if not eligible_entries:
        print(
            "队列共 %d 条，无符合自动发布条件（ACCEPT + HIGH/MEDIUM）的候选。"
            % len(pending_list)
        )
        return 0

    skip_gate = args.skip_link_gate or (
        str(os.environ.get("SKIP_LINK_GATE") or "").strip().lower() in ("1", "true", "yes")
    )
    if skip_gate:
        with mock.patch("apply_reviewed.filter_broken_links", side_effect=_passthrough_gate):
            added, created_brands, skipped, verified, pending_count = apply_reviewed.apply(
                {"accepted": eligible_entries}, competitions_doc, brands_doc
            )
    else:
        added, created_brands, skipped, verified, pending_count = apply_reviewed.apply(
            {"accepted": eligible_entries}, competitions_doc, brands_doc
        )

    # 被跳过的若是因为缺品牌或字段错误，保留在队列中待人工处理；若是重复已存在，则从队列移除
    kept_after_skip = set()
    for item in skipped:
        if item.get("reason") not in DUPLICATE_REASONS:
            kept_after_skip.add(item.get("name"))

    for record in eligible_records:
        if record.get("name") in kept_after_skip:
            remaining_queue.append(record)

    if not args.dry_run:
        if added or created_brands:
            apply_reviewed.dump_json(args.brands, brands_doc)
            apply_reviewed.dump_json(args.competitions, competitions_doc)
        save_queue(args.queue, remaining_queue)

    print(
        "自动发布完成: 新增赛事 %d 条（已核验 %d / 待核验 %d），新建品牌 %d 个，去重/跳过 %d 条，队列剩余 %d 条"
        % (
            len(added),
            verified,
            pending_count,
            len(created_brands),
            len(skipped),
            len(remaining_queue),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
