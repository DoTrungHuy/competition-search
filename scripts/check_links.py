# -*- coding: utf-8 -*-
"""巡检生产数据中的官方链接并分类输出报告。"""
from __future__ import print_function

import argparse
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "reports", "link-check.json")
USER_AGENT = "Mozilla/5.0 (compatible; CompetitionSearchLinkCheck/0.1)"


def load_json(name):
    with open(os.path.join(ROOT, "data", name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def collect_links():
    links = {}

    def add(url, label, source_type):
        if not url:
            return
        links.setdefault(url, {"url": url, "labels": [], "source_types": []})
        if label not in links[url]["labels"]:
            links[url]["labels"].append(label)
        if source_type not in links[url]["source_types"]:
            links[url]["source_types"].append(source_type)

    for brand in load_json("brands.json").get("brands", []):
        add(brand.get("official_home"), brand.get("name"), "brand")
    for portal in load_json("portals.json").get("portals", []):
        add(portal.get("link"), portal.get("name"), "portal")
    for event in load_json("competitions.json").get("competitions", []):
        add(event.get("link"), event.get("name"), "event")
    return list(links.values())


def check_link(entry, timeout):
    result = dict(entry)
    try:
        response = requests.get(
            entry["url"],
            timeout=timeout,
            allow_redirects=True,
            stream=True,
            headers={"User-Agent": USER_AGENT},
        )
        result["status_code"] = response.status_code
        result["final_url"] = response.url
        result["redirect_count"] = len(response.history)
        if response.status_code in (401, 403, 429):
            result["classification"] = "anti_bot"
        elif response.status_code in (404, 410):
            result["classification"] = "broken"
        elif 200 <= response.status_code < 400:
            result["classification"] = (
                "redirect" if response.history or response.url != entry["url"] else "ok"
            )
        else:
            result["classification"] = "http_error"
        response.close()
    except requests.exceptions.SSLError as error:
        result["classification"] = "certificate_error"
        result["error"] = str(error)
    except requests.exceptions.Timeout as error:
        result["classification"] = "timeout"
        result["error"] = str(error)
    except requests.exceptions.RequestException as error:
        result["classification"] = "network_error"
        result["error"] = str(error)
    return result


def main():
    parser = argparse.ArgumentParser(description="巡检赛事、品牌和平台链接")
    parser.add_argument("--out", default=DEFAULT_OUT, help="JSON 报告路径")
    parser.add_argument("--timeout", type=int, default=20, help="单链接超时秒数")
    parser.add_argument("--workers", type=int, default=8, help="并发请求数")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="除正常、重定向和疑似反爬外，其他分类均返回失败",
    )
    args = parser.parse_args()

    links = collect_links()
    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(check_link, entry, args.timeout): entry for entry in links
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["url"])

    counts = Counter(item["classification"] for item in results)
    report = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(results),
        "classifications": dict(sorted(counts.items())),
        "results": results,
    }
    out_dir = os.path.dirname(os.path.abspath(args.out))
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print("链接巡检: %d 条" % len(results))
    for key in sorted(counts):
        print("  %s: %d" % (key, counts[key]))
    print("报告: %s" % args.out)

    if counts.get("broken", 0):
        return 1
    if args.strict:
        allowed = counts.get("ok", 0) + counts.get("redirect", 0) + counts.get("anti_bot", 0)
        if allowed != len(results):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

