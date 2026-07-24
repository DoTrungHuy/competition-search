# -*- coding: utf-8 -*-
"""将旧版赛事数据迁移到可信度显式的 schema v3。

此脚本只允许从 schema v2 迁移一次。无法从官方深链接复核的旧日期会被
移除，并把记录标记为 needs_review，避免页面把推定日期显示成事实。
"""
from __future__ import print_function

import json
import os
import re
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "competitions.json")

REMOVE_IDS = {
    "tianchi-list",
    "tianchi-2025",
    "devpost-hackathons",
    "cxcy-lanqiao-org",
    "cxcy-internetplus-select",
    "cxcy-ciscn-org",
    "ciscn-2026",
}

EDITION_OVERRIDES = {
    "lanqiao-16": "16",
    "lanqiao-17": "17",
    "cnsoftbei-13": "13",
    "cnsoftbei-14": "14",
    "cnsoftbei-15": "15",
}

TRACK_OVERRIDES = {
    "c4-ai-2025": "ai",
    "c4-bigdata-2025": "big-data",
    "c4-net-2025": "network",
    "icpc-2024-regionals": "asia-regionals",
    "icpc-2025-regionals": "asia-regionals",
}

UNVERIFIED_FIELDS = (
    "registration_start",
    "registration_end",
    "competition_start",
    "competition_end",
    "status_override",
    "last_updated",
    "link_type",
)


def derive_edition(item):
    item_id = item.get("id", "")
    if item_id in EDITION_OVERRIDES:
        return EDITION_OVERRIDES[item_id]
    name = item.get("name", "")
    span = re.search(r"(20\d{2})\s*[-/]\s*(20\d{2})", name)
    if span:
        return "%s-%s" % (span.group(1), span.group(2))
    year = re.search(r"20\d{2}", name + " " + item_id)
    return year.group(0) if year else "unknown"


def unverified_record(item):
    record = dict(item)
    for key in UNVERIFIED_FIELDS:
        record.pop(key, None)
    record.pop("link", None)
    record["edition"] = derive_edition(record)
    record["track_id"] = TRACK_OVERRIDES.get(record.get("id"), "main")
    record["last_checked"] = None
    record["needs_review"] = True
    return record


def verified_records():
    return [
        {
            "id": "tianchi-532479-2026",
            "brand_id": "tianchi",
            "edition": "2026",
            "track_id": "ccks-behavior-steering",
            "name": "CCKS2026 任务七：大模型行为调控评测",
            "category": ["人工智能", "自然语言处理"],
            "level": "公开赛事",
            "kind": "大厂赛事",
            "info_channel": "官方渠道",
            "organizer": "中国中文信息学会相关评测任务组",
            "registration_start": "2026-05-01",
            "registration_end": "2026-07-15",
            "competition_start": "2026-05-01",
            "competition_end": "2026-08-15",
            "link": "https://tianchi.aliyun.com/competition/entrance/532479",
            "description": "面向大模型行为引导、知识调控与可控生成的评测任务。",
            "eligibility": "可个人参赛或 2-3 人组队，具体以官方规则为准",
            "tags": ["大模型", "自然语言处理", "天池"],
            "has_campus_notice": False,
            "active": True,
            "last_checked": "2026-07-24",
            "needs_review": False,
        },
        {
            "id": "tianchi-532486-2026",
            "brand_id": "tianchi",
            "edition": "2026",
            "track_id": "afac-agent-memory",
            "name": "AFAC2026 挑战组赛题四：金融长文本 Agent 动态记忆压缩与高效问答",
            "category": ["人工智能", "金融科技"],
            "level": "公开赛事",
            "kind": "大厂赛事",
            "info_channel": "官方渠道",
            "organizer": "AFAC2026 金融智能创新大赛组委会",
            "registration_start": "2026-06-08",
            "registration_end": "2026-07-20",
            "competition_start": "2026-06-08",
            "competition_end": "2026-07-25",
            "link": "https://tianchi.aliyun.com/competition/entrance/532486",
            "description": "面向金融长文本智能体记忆压缩和高效问答的算法挑战。",
            "eligibility": "可个人参赛或最多 3 人组队，具体以官方规则为准",
            "tags": ["智能体", "大模型", "金融科技", "天池"],
            "has_campus_notice": False,
            "active": True,
            "last_checked": "2026-07-24",
            "needs_review": False,
        },
        {
            "id": "ciscn-2026-works",
            "brand_id": "ciscn",
            "edition": "2026",
            "track_id": "works",
            "name": "第十九届全国大学生信息安全竞赛作品赛",
            "category": ["安全"],
            "level": "国家级",
            "kind": "全国赛事",
            "info_channel": "官方渠道",
            "organizer": "全国大学生信息安全竞赛组委会",
            "link": "https://www.ciscn.cn/competition/securityCompetition?compet_id=45",
            "description": "全国大学生信息安全竞赛作品赛，官网当前显示赛道仍在推进。",
            "eligibility": "在校大学生，具体组队和作品要求以官方通知为准",
            "tags": ["网络安全", "信息安全", "作品赛"],
            "has_campus_notice": True,
            "active": True,
            "status_override": "进行中",
            "last_checked": "2026-07-24",
            "needs_review": False,
        },
        {
            "id": "ciscn-2026-innovation",
            "brand_id": "ciscn",
            "edition": "2026",
            "track_id": "innovation-practice",
            "name": "第十九届全国大学生信息安全竞赛创新实践能力赛",
            "category": ["安全"],
            "level": "国家级",
            "kind": "全国赛事",
            "info_channel": "官方渠道",
            "organizer": "全国大学生信息安全竞赛组委会",
            "link": "https://www.ciscn.cn/competition/securityCompetition?compet_id=44",
            "description": "创新实践能力赛独立赛道，当前时间信息仍需进一步核对。",
            "eligibility": "以官方赛道说明为准",
            "tags": ["网络安全", "信息安全"],
            "has_campus_notice": True,
            "active": True,
            "last_checked": "2026-07-24",
            "needs_review": True,
        },
    ]


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("meta", {}).get("schema_version") != 2:
        print("拒绝迁移：只支持 schema v2", file=sys.stderr)
        return 1

    migrated = []
    for item in data.get("competitions", []):
        if item.get("id") in REMOVE_IDS or item.get("id") == "ciscn-2026-works":
            continue
        migrated.append(unverified_record(item))
    migrated.extend(verified_records())

    data["meta"]["schema_version"] = 3
    data["meta"]["date_policy"] = "只有 needs_review=false 的日期参与公开状态计算"
    data["competitions"] = migrated

    with open(DATA_PATH, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print("schema v3: %d 条赛事" % len(migrated))
    return 0


if __name__ == "__main__":
    sys.exit(main())

