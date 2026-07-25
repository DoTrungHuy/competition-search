# -*- coding: utf-8 -*-
"""给已入库的 MLH 记录回填赛程日期。

为什么需要单独一个脚本：`apply_reviewed.py` 只新增、不更新已存在记录
（`id 已存在` 直接 skip），而 `fetch_mlh.py` 也会把存量判为「重复」，
所以只修采集器救不了先前入库的那批无日期记录。

数据来源与采集器完全一致：MLH 赛季页的 schema.org 微数据（官方结构化字段），
按 link 匹配。判定是否转为已核验沿用 `can_auto_verify`（有深链 + 有合法赛程），
与正常管线的结果保持一致，不另立标准。

一次性维护工具，不进周更；默认 --dry-run 之外会直接改写 data/competitions.json。
"""
from __future__ import print_function

import argparse
import json
import os
import sys
import time

import requests

from fetch_mlh import SEASON_URL, USER_AGENT, parse_events
from schedule_utils import (
    SCHEDULE_FIELDS,
    can_auto_verify,
    clean_schedule,
    has_usable_schedule,
    today_iso,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPETITIONS_PATH = os.path.join(ROOT, "data", "competitions.json")


def normalized_url(value):
    return str(value or "").rstrip("/")


def fetch_schedule_map(seasons, timeout, delay):
    """{normalized_link: {competition_start, competition_end}}，只收有日期的。"""
    mapping = {}
    errors = []
    for season in seasons:
        url = SEASON_URL % season
        try:
            response = requests.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=timeout
            )
            response.raise_for_status()
            events = parse_events(response.text)
        except requests.RequestException as error:
            message = "%s -> %s" % (url, error)
            print("失败: %s" % message, file=sys.stderr)
            errors.append(message)
            continue
        dated = 0
        for link, event in events.items():
            if not event.get("competition_start"):
                continue
            mapping[normalized_url(link)] = {
                field: event.get(field) for field in SCHEDULE_FIELDS if event.get(field)
            }
            dated += 1
        print("赛季 %s: %d 个赛事，其中 %d 个带日期" % (season, len(events), dated))
        time.sleep(max(0.0, delay))
    return mapping, errors


def backfill(competitions, schedule_map, today):
    """就地回填，返回 (已更新, 转为已核验, 未匹配) 三份清单。"""
    updated, verified, unmatched = [], [], []
    for item in competitions:
        if item.get("brand_id") != "mlh":
            continue
        if any(item.get(field) for field in SCHEDULE_FIELDS):
            continue  # 已有赛程，不覆盖既有数据
        found = schedule_map.get(normalized_url(item.get("link")))
        if not found:
            unmatched.append(item.get("name"))
            continue

        schedule = clean_schedule(found, "source", "high")
        if not has_usable_schedule(schedule):
            unmatched.append(item.get("name"))
            continue

        for field in SCHEDULE_FIELDS:
            if schedule.get(field):
                item[field] = schedule[field]
        item["schedule_source"] = schedule["schedule_source"]
        item["schedule_confidence"] = schedule["schedule_confidence"]
        updated.append(item.get("name"))

        # 与正常管线同一把尺子：有深链 + 有合法赛程才转已核验。
        if item.get("needs_review") and can_auto_verify(item.get("link"), schedule):
            item["needs_review"] = False
            item["last_checked"] = today
            verified.append(item.get("name"))
    return updated, verified, unmatched


def main():
    parser = argparse.ArgumentParser(description="回填存量 MLH 记录的赛程日期")
    parser.add_argument("--seasons", nargs="*", default=["2026", "2027"])
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--delay", type=float, default=0.8)
    parser.add_argument("--today", default=None, help="写入 last_checked 的日期，便于复现")
    parser.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    args = parser.parse_args()

    today = args.today or today_iso()

    schedule_map, errors = fetch_schedule_map(args.seasons, args.timeout, args.delay)
    if not schedule_map:
        print("没有抓到任何带日期的赛事，中止（不改数据）。", file=sys.stderr)
        return 1

    with open(COMPETITIONS_PATH, "r", encoding="utf-8") as handle:
        doc = json.load(handle)
    competitions = doc.get("competitions", [])

    updated, verified, unmatched = backfill(competitions, schedule_map, today)

    print()
    print("回填 %d 条，其中转为已核验 %d 条；未匹配 %d 条" % (
        len(updated), len(verified), len(unmatched)
    ))
    if unmatched:
        print("未匹配（赛季页已下架或无日期，保持原样）:")
        for name in unmatched[:10]:
            print("  - %s" % name)
        if len(unmatched) > 10:
            print("  ... 另有 %d 条" % (len(unmatched) - 10))

    if args.dry_run:
        print("\n--dry-run：未写入文件。")
        return 0
    if not updated:
        print("无需改动。")
        return 0

    with open(COMPETITIONS_PATH, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print("\n已写入 %s" % COMPETITIONS_PATH)
    print("请接着跑 validate_data.py 与 npm test 作为闸门。")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
