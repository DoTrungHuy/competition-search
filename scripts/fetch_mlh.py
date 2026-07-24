# -*- coding: utf-8 -*-
"""抓取 MLH（Major League Hacking）赛季黑客松，生成待审核草稿。

数据源：https://www.mlh.com/seasons/<season>/events （服务端渲染 HTML）。
赛事名编码在外链的 utm_content 参数里，据此稳定抽取，不依赖易变的 CSS 类。
每个赛事归入 mlh 平台品牌。本脚本不会写入 data/competitions.json。
"""
from __future__ import print_function

import argparse
import os
import re
import sys
import time
from datetime import datetime
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from draft_common import ROOT, categorize, load_production, save_draft, stable_id


DEFAULT_OUT = os.path.join(ROOT, "scripts", "out", "draft_mlh.json")
SEASON_URL = "https://www.mlh.com/seasons/%s/events"
USER_AGENT = "Mozilla/5.0 (compatible; CompetitionSearchMaintainer/0.1)"


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")
    return slug or "event"


def parse_events(html):
    """从赛季页面抽取 {clean_link: name}，只认带 utm_campaign=events 的外链。"""
    soup = BeautifulSoup(html, "html.parser")
    events = {}
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "")
        query = parse_qs(urlparse(href).query)
        if query.get("utm_campaign", [None])[0] != "events":
            continue
        name = unquote(query.get("utm_content", [""])[0]).replace("+", " ").strip()
        clean = href.split("?")[0]
        if name and clean:
            events[clean] = name
    return events


def to_draft_record(name, link, season):
    return {
        "id": stable_id("mlh", link),
        "brand_id": "mlh",
        "edition": season,
        "track_id": "mlh-" + slugify(name),
        "name": name,
        "kind": "国际赛事",
        "info_channel": "官方渠道",
        "link": link,
        "eligibility": "以活动页面为准",
        "description": "MLH 认证的国际黑客松，报名与规则以活动页面为准。",
        "active": True,
        "last_checked": None,
        "needs_review": True,
        "draft": True,
        "source_list": "mlh",
        "source_list_name": "MLH Hackathons",
    }


def main():
    now = datetime.now().year
    parser = argparse.ArgumentParser(description="抓取 MLH 黑客松草稿")
    parser.add_argument("--out", default=DEFAULT_OUT, help="输出草稿 JSON 路径")
    parser.add_argument(
        "--seasons",
        nargs="*",
        default=[str(now), str(now + 1)],
        help="抓取的赛季年份（默认当年与次年）",
    )
    parser.add_argument("--timeout", type=int, default=25, help="请求超时秒数")
    parser.add_argument("--delay", type=float, default=0.8, help="赛季间隔秒")
    args = parser.parse_args()

    accepted = []
    errors = []
    seen = set()
    for season in args.seasons:
        url = SEASON_URL % season
        try:
            response = requests.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=args.timeout
            )
            response.raise_for_status()
            events = parse_events(response.text)
            print("赛季 %s: 抽到 %d 个赛事" % (season, len(events)))
            for link, name in events.items():
                if link in seen:
                    continue
                seen.add(link)
                accepted.append(to_draft_record(name, link, season))
        except requests.RequestException as error:
            message = "%s -> %s" % (url, error)
            print("失败: %s" % message, file=sys.stderr)
            errors.append(message)
        time.sleep(max(0.0, args.delay))

    categorized = categorize(accepted, [], load_production())
    counts = save_draft(args.out, "mlh.com", categorized, errors)
    print(
        "完成: 新增 {new} / 变更 {changed} / 重复 {duplicate} / 拒绝 {rejected}".format(
            **counts
        )
    )
    print("草稿: %s" % args.out)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
