# -*- coding: utf-8 -*-
"""采集脚本共用的草稿 ID、去重分类与落盘逻辑。

供多个来源的 fetch_*.py 复用，保证所有草稿结构一致：

    { "meta": {...}, "review": { "new", "changed", "duplicate", "rejected" } }

不写入 data/competitions.json。
"""
from __future__ import print_function

import hashlib
import json
import os
from datetime import datetime


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTION_DATA = os.path.join(ROOT, "data", "competitions.json")


def stable_id(prefix, url, published_at=None):
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    day = (published_at or "unknown").replace("-", "")
    return "%s-%s-%s" % (prefix, day, digest)


def load_production():
    with open(PRODUCTION_DATA, "r", encoding="utf-8") as handle:
        return json.load(handle).get("competitions", [])


def categorize(records, rejected, production):
    """按 id 与深链接跟生产数据比对，分成 new / changed / duplicate / rejected。"""
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
        if link and link in seen_links:
            result["duplicate"].append(
                {
                    "id": record.get("id"),
                    "name": record.get("name"),
                    "link": link,
                    "reason": "同一次采集重复出现",
                }
            )
            continue
        if link:
            seen_links.add(link)

        existing = production_by_id.get(record.get("id"))
        if not existing and link:
            existing = production_by_link.get(link)
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
                    "id": record.get("id"),
                    "name": record.get("name"),
                    "link": link,
                    "reason": "生产数据已存在",
                }
            )
    return result


def save_draft(out_path, source, categorized, errors=None):
    counts = {key: len(value) for key, value in categorized.items()}
    output = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source": source,
            "counts": counts,
            "errors": errors or [],
            "note": "审核草稿，不会自动写入 data/competitions.json",
        },
        "review": categorized,
    }
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return counts
