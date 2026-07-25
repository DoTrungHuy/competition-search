# -*- coding: utf-8 -*-
"""对本轮新增/变更的赛事深链做可达性闸：仅 404/410 剥离 link。"""
from __future__ import print_function

import argparse
import json
import os
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_AGENT = "Mozilla/5.0 (compatible; CompetitionSearchLinkGate/0.1)"


def classify_status(code):
    if code in (404, 410):
        return "broken"
    if code in (401, 403, 429):
        return "anti_bot"
    if 200 <= code < 400:
        return "ok"
    return "http_error"


def check_url(url, timeout=15, get=None):
    get = get or requests.get
    try:
        response = get(
            url,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
            headers={"User-Agent": USER_AGENT},
        )
        code = response.status_code
        response.close()
        return classify_status(code), code
    except requests.exceptions.RequestException:
        # 网络/证书问题不挡入库
        return "network_or_tls", None


def filter_broken_links(records, timeout=15, get=None):
    """就地或复制列表：404/410 则去掉 link。返回 (records, dropped)."""
    dropped = []
    for item in records or []:
        link = item.get("link")
        if not link:
            continue
        kind, code = check_url(link, timeout=timeout, get=get)
        if kind == "broken":
            dropped.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "link": link,
                    "status_code": code,
                }
            )
            item.pop("link", None)
            # 无深链则不能当已核验完整记录——若已是 verified，降为 needs_review
            if item.get("needs_review") is False:
                item["needs_review"] = True
                item["last_checked"] = None
                for field in (
                    "registration_start",
                    "registration_end",
                    "competition_start",
                    "competition_end",
                ):
                    item.pop(field, None)
    return records, dropped


def main():
    """可选 CLI：对整表 competitions 的 link 跑闸（维护用）。默认读 data。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="写回 data/competitions.json（默认只打印将剥离的 link）",
    )
    args = parser.parse_args()
    path = os.path.join(ROOT, "data", "competitions.json")
    with open(path, "r", encoding="utf-8") as handle:
        doc = json.load(handle)
    # 维护全表时只剥离 404/410，不自动 degraded
    _, dropped = filter_broken_links(doc.get("competitions"), timeout=args.timeout)
    print("would_drop=%d" % len(dropped))
    for row in dropped:
        print("  %s %s %s" % (row.get("id"), row.get("status_code"), row.get("link")))
    if args.apply and dropped:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(doc, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print("wrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
