# -*- coding: utf-8 -*-
"""抓取南邮创新创业教育学院通知，生成待人工审核的分类草稿。

本脚本不会写入 data/competitions.json。
"""
from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from source_config import SourceConfigError, load_sources


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "scripts", "out", "draft_campus.json")
PRODUCTION_DATA = os.path.join(ROOT, "data", "competitions.json")


class ParseError(ValueError):
    pass


def fetch(url, user_agent, timeout=25):
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": user_agent},
    )
    response.raise_for_status()
    return response.content


def parse_list_html(html, base, selectors, allow_empty=False):
    """按 YAML 中的 CSS selector 解析列表，优先读取完整 title 属性。"""
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select(selectors["item"])
    if not blocks:
        if allow_empty:
            return []
        raise ParseError("未匹配到列表项，页面结构可能已变化")

    items = []
    for block in blocks:
        anchor = block.select_one(selectors["link"])
        if not anchor:
            continue
        href = str(anchor.get("href") or "").strip()
        if not href or "page.htm" not in href:
            continue
        title = str(anchor.get("title") or "").strip()
        if not title:
            title = " ".join(anchor.get_text(" ", strip=True).split())
        date_node = block.select_one(selectors["date"])
        date_text = date_node.get_text(" ", strip=True) if date_node else ""
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", date_text)
        if not title:
            continue
        items.append(
            {
                "title": title,
                "url": urljoin(base.rstrip("/") + "/", href),
                "published_at": date_match.group(0) if date_match else None,
            }
        )
    if not items:
        if allow_empty:
            return []
        raise ParseError("列表项存在，但没有解析到有效通知链接")
    return items


def classify_title(title, include_any, exclude_any):
    text = title or ""
    for keyword in exclude_any:
        if keyword and keyword.lower() in text.lower():
            return False, "命中排除词: %s" % keyword
    if not include_any:
        return True, "未配置包含词"
    for keyword in include_any:
        if keyword and keyword.lower() in text.lower():
            return True, "命中竞赛词: %s" % keyword
    return False, "未命中竞赛关键词"


def guess_kind(title):
    text = title or ""
    if any(keyword in text for keyword in ("天池", "华为", "字节", "腾讯", "阿里", "百度")):
        return "大厂赛事"
    if any(keyword in text for keyword in ("MCM", "ICM", "ICPC", "国际")):
        return "国际赛事"
    if "南京邮电大学" in text and any(keyword in text for keyword in ("校赛", "校内")):
        return "校级赛事"
    return "全国赛事"


def guess_brand_id(title):
    text = title or ""
    mappings = (
        ("蓝桥", "lanqiao"),
        ("中国国际大学生创新大赛", "internetplus"),
        ("互联网+", "internetplus"),
        ("信息安全竞赛", "ciscn"),
        ("物联网设计竞赛", "iot"),
        ("软件杯", "cnsoftbei"),
        ("天梯", "gplt"),
        ("华为 ICT", "huawei_ict"),
        ("华为软件精英", "huawei_codecraft"),
    )
    for keyword, brand_id in mappings:
        if keyword in text:
            return brand_id
    return None


def derive_edition(title):
    match = re.search(r"20\d{2}", title or "")
    return match.group(0) if match else "unknown"


def stable_id(url, published_at=None):
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    day = (published_at or "unknown").replace("-", "")
    return "campus-%s-%s" % (day, digest)


def to_draft_record(item, list_meta):
    title = item["title"]
    digest = hashlib.sha256(item["url"].encode("utf-8")).hexdigest()[:10]
    return {
        "id": stable_id(item["url"], item.get("published_at")),
        "brand_id": guess_brand_id(title),
        "edition": derive_edition(title),
        "track_id": "campus-notice-" + digest,
        "name": title,
        "kind": guess_kind(title),
        "info_channel": "校内官网",
        "link": item["url"],
        "published_at": item.get("published_at"),
        "eligibility": "以通知原文为准",
        "description": "学校网站通知，赛事主办与规则以通知和赛事官网为准。",
        "has_campus_notice": True,
        "active": True,
        "last_checked": None,
        "needs_review": True,
        "source_list": list_meta.get("id"),
        "source_list_name": list_meta.get("name"),
        "draft": True,
    }


def load_production():
    with open(PRODUCTION_DATA, "r", encoding="utf-8") as handle:
        return json.load(handle).get("competitions", [])


def categorize(records, rejected, production):
    production_by_id = {item.get("id"): item for item in production}
    production_by_link = {
        item.get("link"): item for item in production if item.get("link")
    }
    seen_links = set()
    result = {
        "new": [],
        "changed": [],
        "duplicate": [],
        "rejected": list(rejected),
    }

    for record in records:
        link = record.get("link")
        if link in seen_links:
            result["duplicate"].append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "link": link,
                    "reason": "同一次采集重复出现",
                }
            )
            continue
        seen_links.add(link)

        existing = production_by_id.get(record["id"]) or production_by_link.get(link)
        if not existing:
            result["new"].append(record)
            continue

        comparable = ("name", "published_at", "link")
        changed_fields = [
            field for field in comparable if existing.get(field) != record.get(field)
        ]
        if changed_fields:
            result["changed"].append(
                {
                    "record": record,
                    "existing_id": existing.get("id"),
                    "changed_fields": changed_fields,
                }
            )
        else:
            result["duplicate"].append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "link": link,
                    "reason": "生产数据已存在",
                }
            )
    return result


def main():
    parser = argparse.ArgumentParser(description="拉取创学院竞赛相关通知列表")
    parser.add_argument("--out", default=DEFAULT_OUT, help="输出草稿 JSON 路径")
    parser.add_argument("--delay", type=float, default=0.8, help="请求间隔秒")
    parser.add_argument("--all-titles", action="store_true", help="不过滤关键词")
    args = parser.parse_args()

    try:
        sources = load_sources()
    except SourceConfigError as error:
        print("配置错误: %s" % error, file=sys.stderr)
        return 1

    config = sources["campus"]
    base = config["base"].rstrip("/")
    selectors = config["selectors"]
    timeout = int(config.get("timeout_seconds", 25))
    accepted_records = []
    rejected = []
    errors = []

    for source_list in config["lists"]:
        url = urljoin(base + "/", str(source_list.get("path") or "").lstrip("/"))
        print("抓取: %s (%s)" % (source_list.get("name"), url))
        try:
            parsed = parse_list_html(
                fetch(url, config["user_agent"], timeout),
                base,
                selectors,
                bool(source_list.get("allow_empty")),
            )
            print("  解析到 %d 条" % len(parsed))
            for item in parsed:
                accepted, reason = classify_title(
                    item["title"],
                    config.get("title_include_any") or [],
                    config.get("title_exclude_any") or [],
                )
                if args.all_titles:
                    accepted = True
                    reason = "all-titles 模式"
                if accepted:
                    accepted_records.append(to_draft_record(item, source_list))
                else:
                    rejected.append(
                        {
                            "name": item["title"],
                            "link": item["url"],
                            "published_at": item.get("published_at"),
                            "source_list": source_list.get("id"),
                            "reason": reason,
                        }
                    )
        except (requests.RequestException, ParseError, ValueError) as error:
            message = "%s -> %s" % (url, error)
            print("  失败: %s" % message, file=sys.stderr)
            errors.append(message)
        time.sleep(max(0.0, args.delay))

    categorized = categorize(accepted_records, rejected, load_production())
    counts = {key: len(value) for key, value in categorized.items()}
    output = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source": "cxcy.njupt.edu.cn",
            "counts": counts,
            "errors": errors,
            "note": "审核草稿，不会自动写入 data/competitions.json",
        },
        "review": categorized,
    }

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(
        "完成: 新增 {new} / 变更 {changed} / 重复 {duplicate} / 拒绝 {rejected}".format(
            **counts
        )
    )
    print("草稿: %s" % args.out)
    if errors:
        print("有 %d 个列表失败，见 meta.errors" % len(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
