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
from platform_text import description_for, eligibility_for


DEFAULT_OUT = os.path.join(ROOT, "scripts", "out", "draft_mlh.json")
SEASON_URL = "https://www.mlh.com/seasons/%s/events"
USER_AGENT = "Mozilla/5.0 (compatible; CompetitionSearchMaintainer/0.1)"


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")
    return slug or "event"


def iso_date(value):
    """把 schema.org 的 2026-07-24T15:01:00Z 取成 2026-07-24。

    赛季页给的是带 Z 的 UTC 时刻，这里只取日期部分：黑客松跨度以天计，
    时区差最多让边界日错一天，不值得为此引入 tz 依赖；宁可少写也不臆造。
    """
    text = str(value or "").strip()
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if not match:
        return None
    try:
        datetime.strptime(match.group(0), "%Y-%m-%d")
    except ValueError:
        return None
    return match.group(0)


def event_meta(anchor, prop):
    """只取本赛事自身的 itemprop，排除嵌套 location/address 里的同名字段。"""
    for meta in anchor.find_all("meta", attrs={"itemprop": prop}):
        parent = meta.find_parent(attrs={"itemscope": True})
        if parent is not anchor:
            continue  # 落在 Place/PostalAddress 等子作用域里，不是赛事本身的
        content = str(meta.get("content") or "").strip()
        if content:
            return content
    return None


def parse_events(html):
    """抽取 {clean_link: {name, competition_start, competition_end}}。

    赛事卡片是 a[itemtype=schema.org/Event]，日期在其直接子 meta[itemprop] 中；
    名字仍从外链 utm_content 取（页面里的 itemprop=name 属于嵌套的 location）。
    """
    soup = BeautifulSoup(html, "html.parser")
    events = {}
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "")
        query = parse_qs(urlparse(href).query)
        if query.get("utm_campaign", [None])[0] != "events":
            continue
        name = unquote(query.get("utm_content", [""])[0]).replace("+", " ").strip()
        clean = href.split("?")[0]
        if not (name and clean):
            continue
        events[clean] = {
            "name": name,
            "competition_start": iso_date(event_meta(anchor, "startDate")),
            "competition_end": iso_date(event_meta(anchor, "endDate")),
        }
    return events


def to_draft_record(event, link, season):
    name = event["name"]
    record = {
        "id": stable_id("mlh", link),
        "brand_id": "mlh",
        "edition": season,
        "track_id": "mlh-" + slugify(name),
        "name": name,
        "kind": "国际赛事",
        "info_channel": "官方渠道",
        "link": link,
        "active": True,
        "last_checked": None,
        "needs_review": True,
        "draft": True,
        "source_list": "mlh",
        "source_list_name": "MLH Hackathons",
    }
    # 源侧结构化赛程：schedule_from_source_record 会优先采信（confidence=high），
    # 有深链 + 有赛程时 apply_reviewed 便可自动转已核验，不必让模型臆造日期。
    for field in ("competition_start", "competition_end"):
        if event.get(field):
            record[field] = event[field]
    # 每条带上赛事名，禁止全站统一「以活动页面为准」
    record["eligibility"] = eligibility_for(record, "mlh")
    record["description"] = description_for(record, "mlh")
    return record


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
            dated = sum(1 for e in events.values() if e.get("competition_start"))
            print(
                "赛季 %s: 抽到 %d 个赛事（含日期 %d 个）"
                % (season, len(events), dated)
            )
            for link, event in events.items():
                if link in seen:
                    continue
                seen.add(link)
                accepted.append(to_draft_record(event, link, season))
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
