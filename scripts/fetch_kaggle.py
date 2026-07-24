# -*- coding: utf-8 -*-
"""抓取 Kaggle 竞赛列表，生成待审核草稿。

数据源：https://www.kaggle.com/api/v1/competitions/list （官方 API，返回 JSON）。
需要环境变量 KAGGLE_USERNAME 与 KAGGLE_KEY（来自 kaggle.json）。
缺少凭据时优雅跳过，不视为失败。每条归入 kaggle 平台品牌。
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


DEFAULT_OUT = os.path.join(ROOT, "scripts", "out", "draft_kaggle.json")
API_URL = "https://www.kaggle.com/api/v1/competitions/list"
USER_AGENT = "Mozilla/5.0 (compatible; CompetitionSearchMaintainer/0.1)"
# 入门/沙盒类不是正式竞赛，直接排除。
SKIP_CATEGORIES = {"Getting Started", "Playground"}


def competition_url(item):
    url = str(item.get("url") or "").strip()
    if url.startswith("http"):
        return url
    ref = str(item.get("ref") or "").strip()
    if ref.startswith("http"):
        return ref
    return "https://www.kaggle.com/competitions/%s" % ref if ref else ""


def derive_edition(item):
    text = str(item.get("deadline") or "")
    match = re.search(r"20\d{2}", text)
    return match.group(0) if match else str(datetime.now().year)


def to_draft_record(item):
    url = competition_url(item)
    ref = str(item.get("ref") or "").rstrip("/").split("/")[-1]
    deadline = str(item.get("deadline") or "").strip() or None
    enabled = str(item.get("enabledDate") or "").strip() or None
    return {
        "id": stable_id("kaggle", url),
        "brand_id": "kaggle",
        "edition": derive_edition(item),
        "track_id": "kaggle-" + (ref or stable_id("k", url)),
        "name": " ".join(str(item.get("title") or "").split()),
        "kind": "大厂赛事",
        "info_channel": "官方渠道",
        "organizer": item.get("organizationName"),
        "link": url,
        "eligibility": "以赛题页面为准",
        "description": "Kaggle 平台数据科学竞赛，报名与规则以赛题页面为准。",
        "active": True,
        "last_checked": None,
        "needs_review": True,
        "draft": True,
        "source_list": "kaggle",
        "source_list_name": "Kaggle Competitions",
        "deadline": deadline,
        "source_schedule_text": deadline,
        "raw_schedule": {
            "deadline": deadline,
            "enabledDate": enabled,
        },
    }


def fetch_page(page, timeout, auth):
    response = requests.get(
        API_URL,
        params={"page": page},
        auth=auth,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def main():
    parser = argparse.ArgumentParser(description="抓取 Kaggle 竞赛草稿")
    parser.add_argument("--out", default=DEFAULT_OUT, help="输出草稿 JSON 路径")
    parser.add_argument("--pages", type=int, default=2, help="抓取页数（每页约 20 条）")
    parser.add_argument("--timeout", type=int, default=25, help="请求超时秒数")
    parser.add_argument("--delay", type=float, default=0.8, help="翻页间隔秒")
    args = parser.parse_args()

    username = os.environ.get("KAGGLE_USERNAME")
    key = os.environ.get("KAGGLE_KEY")
    if not username or not key:
        print("跳过 Kaggle：未配置 KAGGLE_USERNAME / KAGGLE_KEY")
        return 0

    accepted = []
    rejected = []
    errors = []
    try:
        for page in range(1, args.pages + 1):
            batch = fetch_page(page, args.timeout, (username, key))
            if not batch:
                break
            for item in batch:
                if not item.get("title"):
                    continue
                if item.get("category") in SKIP_CATEGORIES:
                    rejected.append(
                        {
                            "name": item.get("title"),
                            "link": competition_url(item),
                            "reason": "入门/沙盒类别: %s" % item.get("category"),
                        }
                    )
                    continue
                accepted.append(to_draft_record(item))
            time.sleep(max(0.0, args.delay))
    except (requests.RequestException, ValueError) as error:
        message = "%s -> %s" % (API_URL, error)
        print("失败: %s" % message, file=sys.stderr)
        errors.append(message)

    categorized = categorize(accepted, rejected, load_production())
    counts = save_draft(args.out, "kaggle.com", categorized, errors)
    print(
        "完成: 新增 {new} / 变更 {changed} / 重复 {duplicate} / 拒绝 {rejected}".format(
            **counts
        )
    )
    print("草稿: %s" % args.out)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
