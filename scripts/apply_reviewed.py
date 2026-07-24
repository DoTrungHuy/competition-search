# -*- coding: utf-8 -*-
"""把 DeepSeek 审核通过的候选合并进生产数据。

流程定位（自动化管线的第三步）：

    reviewed.json -> [本脚本] -> data/competitions.json (+ data/brands.json)

只写入 needs_review=true 的记录：公开页面仅显示「见官网详情」，
不含推断日期。对不上已有品牌、但 DeepSeek 提议了合法新品牌时，
自动在 brands.json 建该品牌（校验 URL、按 id/官网/名称去重）。

产出仍需 validate_data.py + npm test 作为闸门；本脚本不推送。
"""
from __future__ import print_function

import argparse
import json
import os
import sys
from urllib.parse import urlparse


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DEFAULT_IN = os.path.join(ROOT, "scripts", "out", "reviewed.json")

KINDS = ("全国赛事", "大厂赛事", "国际赛事", "校级赛事")
# 从草稿记录带入生产记录的白名单字段（不含任何推断赛程字段）。
CARRY_FIELDS = (
    "id",
    "edition",
    "track_id",
    "name",
    "info_channel",
    "published_at",
    "eligibility",
    "description",
    "has_campus_notice",
)


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def normalized_url(value):
    return str(value or "").rstrip("/").lower()


def valid_url(value):
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


class BrandResolver:
    """在已有品牌里查找，找不到就按提议新建。"""

    def __init__(self, brands):
        self.brands = brands
        self.by_id = {b.get("brand_id"): b for b in brands}
        self.by_home = {
            normalized_url(b.get("official_home")): b for b in brands if b.get("official_home")
        }
        self.by_name = {str(b.get("name") or "").strip(): b for b in brands if b.get("name")}
        self.created = []

    def resolve(self, brand_id, new_brand):
        if brand_id and brand_id in self.by_id:
            return brand_id
        if not new_brand:
            return None
        # 去重：id / 官网 / 名称任一撞上就复用已有品牌
        existing = (
            self.by_id.get(new_brand["brand_id"])
            or self.by_home.get(normalized_url(new_brand["official_home"]))
            or self.by_name.get(new_brand["name"].strip())
        )
        if existing:
            return existing.get("brand_id")
        if new_brand["kind"] not in KINDS or not valid_url(new_brand["official_home"]):
            return None
        brand = {
            "brand_id": new_brand["brand_id"],
            "name": new_brand["name"],
            "kind": new_brand["kind"],
            "official_home": new_brand["official_home"],
            "aliases": [],
            "priority_tier": "P3",
            "active": True,
            "auto_added": True,
        }
        self.brands.append(brand)
        self.by_id[brand["brand_id"]] = brand
        self.by_home[normalized_url(brand["official_home"])] = brand
        self.by_name[brand["name"].strip()] = brand
        self.created.append(brand["brand_id"])
        return brand["brand_id"]


def build_record(source, brand_id, kind, brand_home):
    record = {}
    for field in CARRY_FIELDS:
        if source.get(field) is not None:
            record[field] = source[field]
    record["brand_id"] = brand_id
    record["kind"] = kind
    record["active"] = True
    record["needs_review"] = True
    record["last_checked"] = None
    # link 允许缺省（前端回退品牌官网）；但不能等于品牌首页。
    link = source.get("link")
    if link and normalized_url(link) != normalized_url(brand_home):
        record["link"] = link
    record.setdefault("edition", "unknown")
    record.setdefault("eligibility", "以通知原文为准")
    return record


def apply(reviewed, competitions_doc, brands_doc):
    competitions = competitions_doc.setdefault("competitions", [])
    brands = brands_doc.setdefault("brands", [])
    resolver = BrandResolver(brands)

    existing_ids = {c.get("id") for c in competitions}
    existing_links = {normalized_url(c.get("link")) for c in competitions if c.get("link")}
    existing_keys = {
        (c.get("brand_id"), str(c.get("edition")), c.get("track_id")) for c in competitions
    }

    added = []
    skipped = []
    for entry in reviewed.get("accepted", []):
        source = entry.get("record") or {}
        decision = entry.get("decision") or {}
        name = source.get("name")

        brand_id = resolver.resolve(decision.get("brand_id"), decision.get("new_brand"))
        if not brand_id:
            skipped.append({"name": name, "reason": "无可用品牌（对不上且无合法新品牌提议）"})
            continue

        kind = decision.get("kind") if decision.get("kind") in KINDS else source.get("kind")
        if kind not in KINDS:
            skipped.append({"name": name, "reason": "kind 非法"})
            continue

        brand_home = resolver.by_id[brand_id].get("official_home")
        record = build_record(source, brand_id, kind, brand_home)

        if not record.get("id") or not record.get("track_id"):
            skipped.append({"name": name, "reason": "缺少 id 或 track_id"})
            continue
        key = (record["brand_id"], str(record["edition"]), record["track_id"])
        link_norm = normalized_url(record.get("link"))
        if record["id"] in existing_ids:
            skipped.append({"name": name, "reason": "id 已存在"})
            continue
        if key in existing_keys:
            skipped.append({"name": name, "reason": "品牌/届次/赛道已存在"})
            continue
        if record.get("link") and link_norm in existing_links:
            skipped.append({"name": name, "reason": "深链接已存在"})
            continue

        competitions.append(record)
        existing_ids.add(record["id"])
        existing_keys.add(key)
        if record.get("link"):
            existing_links.add(link_norm)
        added.append({"name": name, "brand_id": brand_id})

    return added, resolver.created, skipped


def main():
    parser = argparse.ArgumentParser(description="合并审核通过的候选进生产数据")
    parser.add_argument("--in", dest="infile", default=DEFAULT_IN, help="reviewed.json 路径")
    parser.add_argument("--competitions", default=os.path.join(DATA_DIR, "competitions.json"))
    parser.add_argument("--brands", default=os.path.join(DATA_DIR, "brands.json"))
    parser.add_argument("--dry-run", action="store_true", help="只报告不写文件")
    args = parser.parse_args()

    if not os.path.isfile(args.infile):
        print("找不到审核结果: %s" % args.infile, file=sys.stderr)
        return 2

    reviewed = load_json(args.infile)
    competitions_doc = load_json(args.competitions)
    brands_doc = load_json(args.brands)

    added, created_brands, skipped = apply(reviewed, competitions_doc, brands_doc)

    if not args.dry_run and (added or created_brands):
        dump_json(args.brands, brands_doc)
        dump_json(args.competitions, competitions_doc)

    print("新增赛事: %d" % len(added))
    for item in added:
        print("  + %s [%s]" % (item["name"], item["brand_id"]))
    print("自动新建品牌: %d %s" % (len(created_brands), created_brands or ""))
    print("跳过: %d" % len(skipped))
    for item in skipped:
        print("  - %s（%s）" % (item["name"], item["reason"]))
    if args.dry_run:
        print("[dry-run] 未写入文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
