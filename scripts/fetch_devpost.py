# -*- coding: utf-8 -*-
"""抓取 Devpost 平台的在线黑客松，生成待人工/审核的分类草稿。

数据源：https://devpost.com/api/hackathons （返回 JSON）。
每个 hackathon 归入 devpost 平台品牌，作为一条 needs_review 赛事草稿。
本脚本不会写入 data/competitions.json。
"""
from __future__ import print_function

import argparse
import os
import re
import sys
import time
from datetime import datetime

import requests

from draft_common import ROOT, categorize, load_production, save_draft, stable_id


DEFAULT_OUT = os.path.join(ROOT, "scripts", "out", "draft_devpost.json")
API_URL = "https://devpost.com/api/hackathons"
USER_AGENT = "Mozilla/5.0 (compatible; CompetitionSearchMaintainer/0.1)"


def derive_edition(hackathon):
    text = str(hackathon.get("submission_period_dates") or "")
    match = re.search(r"20\d{2}", text)
    return match.group(0) if match else str(datetime.now().year)


def to_draft_record(hackathon):
    url = str(hackathon.get("url") or "").strip()
    title = " ".join(str(hackathon.get("title") or "").split())
    period = str(hackathon.get("submission_period_dates") or "").strip() or None
    return {
        "id": stable_id("devpost", url),
        "brand_id": "devpost",
        "edition": derive_edition(hackathon),
        "track_id": "devpost-%s" % hackathon.get("id"),
        "name": title,
        "kind": "国际赛事",
        "info_channel": "官方渠道",
        "organizer": hackathon.get("organization_name"),
        "link": url,
        "eligibility": "以活动页面为准",
        "description": "Devpost 平台国际黑客松，报名与规则以活动页面为准。",
        "active": True,
        "last_checked": None,
        "needs_review": True,
        "draft": True,
        "source_list": "devpost",
        "source_list_name": "Devpost Hackathons",
        # 源侧时间线索：审核阶段优先解析，无需模型臆造
        "source_schedule_text": period,
        "raw_schedule": {
            "submission_period_dates": period,
            "open_state": hackathon.get("open_state"),
            "time_left": hackathon.get("time_left"),
        },
    }


def fetch_hackathons(pages, timeout, delay):
    items = []
    for page in range(1, pages + 1):
        params = [
            ("challenge_type[]", "online"),
            ("status[]", "open"),
            ("status[]", "upcoming"),
            ("order_by", "deadline"),
            ("page", str(page)),
        ]
        response = requests.get(
            API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout
        )
        response.raise_for_status()
        batch = response.json().get("hackathons", [])
        if not batch:
            break
        items.extend(batch)
        time.sleep(max(0.0, delay))
    return items


def main():
    parser = argparse.ArgumentParser(description="抓取 Devpost 黑客松草稿")
    parser.add_argument("--out", default=DEFAULT_OUT, help="输出草稿 JSON 路径")
    parser.add_argument("--pages", type=int, default=2, help="抓取页数（每页约 10-12 条）")
    parser.add_argument("--timeout", type=int, default=25, help="请求超时秒数")
    parser.add_argument("--delay", type=float, default=0.8, help="翻页间隔秒")
    args = parser.parse_args()

    errors = []
    accepted = []
    rejected = []
    try:
        hackathons = fetch_hackathons(args.pages, args.timeout, args.delay)
        print("抓取到 %d 个 hackathon" % len(hackathons))
        for hackathon in hackathons:
            if not hackathon.get("url") or not hackathon.get("title"):
                continue
            if hackathon.get("invite_only"):
                rejected.append(
                    {
                        "name": hackathon.get("title"),
                        "link": hackathon.get("url"),
                        "reason": "仅限邀请",
                    }
                )
                continue
            accepted.append(to_draft_record(hackathon))
    except (requests.RequestException, ValueError) as error:
        message = "%s -> %s" % (API_URL, error)
        print("失败: %s" % message, file=sys.stderr)
        errors.append(message)

    categorized = categorize(accepted, rejected, load_production())
    counts = save_draft(args.out, "devpost.com", categorized, errors)
    print(
        "完成: 新增 {new} / 变更 {changed} / 重复 {duplicate} / 拒绝 {rejected}".format(
            **counts
        )
    )
    print("草稿: %s" % args.out)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
