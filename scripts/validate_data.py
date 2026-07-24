# -*- coding: utf-8 -*-
"""校验生产赛事、品牌和平台入口数据。"""
from __future__ import print_function

import json
import os
import sys
from datetime import datetime
from urllib.parse import urlparse


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DATE_FIELDS = (
    "registration_start",
    "registration_end",
    "competition_start",
    "competition_end",
    "published_at",
    "last_checked",
)
REQUIRED_EVENT_FIELDS = (
    "id",
    "brand_id",
    "edition",
    "track_id",
    "name",
    "kind",
    "info_channel",
    "eligibility",
    "active",
    "needs_review",
    "last_checked",
)
KINDS = {"全国赛事", "大厂赛事", "国际赛事", "校级赛事"}
STATUS_OVERRIDES = {
    "报名中",
    "即将开始报名",
    "即将开始",
    "进行中",
    "报名结束",
    "已结束",
    "已停办",
}


def load_json(name):
    path = os.path.join(DATA_DIR, name)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def valid_date(value):
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def valid_url(value):
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def normalized_url(value):
    return str(value or "").rstrip("/")


def validate():
    errors = []
    warnings = []
    competitions = load_json("competitions.json")
    brands_doc = load_json("brands.json")
    portals_doc = load_json("portals.json")

    if competitions.get("meta", {}).get("schema_version") != 3:
        errors.append("competitions.json 必须使用 schema_version 3")

    brands = {}
    for index, brand in enumerate(brands_doc.get("brands", [])):
        prefix = "brands[%d]" % index
        brand_id = brand.get("brand_id")
        if not brand_id:
            errors.append("%s 缺少 brand_id" % prefix)
            continue
        if brand_id in brands:
            errors.append("品牌 ID 重复: %s" % brand_id)
        brands[brand_id] = brand
        if brand.get("kind") not in KINDS:
            errors.append("%s kind 非法: %s" % (prefix, brand.get("kind")))
        if not valid_url(brand.get("official_home")):
            errors.append("%s official_home 非法" % prefix)

    portal_ids = set()
    for index, portal in enumerate(portals_doc.get("portals", [])):
        prefix = "portals[%d]" % index
        portal_id = portal.get("id")
        if not portal_id:
            errors.append("%s 缺少 id" % prefix)
        elif portal_id in portal_ids:
            errors.append("平台 ID 重复: %s" % portal_id)
        portal_ids.add(portal_id)
        if portal.get("kind") not in KINDS:
            errors.append("%s kind 非法" % prefix)
        if not valid_url(portal.get("link")):
            errors.append("%s link 非法" % prefix)
        if not valid_date(portal.get("last_checked")):
            errors.append("%s last_checked 非法" % prefix)

    event_ids = set()
    edition_keys = set()
    event_links = set()
    verified_active = 0
    review_count = 0

    for index, item in enumerate(competitions.get("competitions", [])):
        prefix = "competitions[%d]" % index
        missing = [key for key in REQUIRED_EVENT_FIELDS if key not in item]
        if missing:
            errors.append("%s 缺少字段: %s" % (prefix, ", ".join(missing)))
            continue

        event_id = item.get("id")
        if event_id in event_ids:
            errors.append("赛事 ID 重复: %s" % event_id)
        event_ids.add(event_id)

        unique_key = (
            item.get("brand_id"),
            str(item.get("edition")),
            item.get("track_id"),
        )
        if unique_key in edition_keys:
            errors.append("品牌/届次/赛道重复: %s" % (unique_key,))
        edition_keys.add(unique_key)

        brand = brands.get(item.get("brand_id"))
        if not brand:
            errors.append("%s 引用了不存在的 brand_id: %s" % (prefix, item.get("brand_id")))
            continue

        if item.get("kind") not in KINDS:
            errors.append("%s kind 非法: %s" % (prefix, item.get("kind")))
        if "last_updated" in item:
            errors.append("%s 不应继续保存 last_updated" % prefix)
        if not isinstance(item.get("needs_review"), bool):
            errors.append("%s needs_review 必须是布尔值" % prefix)

        for field in DATE_FIELDS:
            if field in item and not valid_date(item.get(field)):
                errors.append("%s %s 日期非法: %s" % (prefix, field, item.get(field)))

        if (
            item.get("registration_start")
            and item.get("registration_end")
            and item["registration_start"] > item["registration_end"]
        ):
            errors.append("%s 报名开始晚于报名截止" % prefix)
        if (
            item.get("competition_start")
            and item.get("competition_end")
            and item["competition_start"] > item["competition_end"]
        ):
            errors.append("%s 比赛开始晚于比赛结束" % prefix)

        link = item.get("link")
        if link:
            if not valid_url(link):
                errors.append("%s link 非法" % prefix)
            if normalized_url(link) == normalized_url(brand.get("official_home")):
                errors.append("%s link 不能与品牌首页相同" % prefix)
            if link in event_links:
                errors.append("赛事深链接重复: %s" % link)
            event_links.add(link)

        if item.get("status_override") and item.get("status_override") not in STATUS_OVERRIDES:
            errors.append("%s status_override 非法" % prefix)

        if item.get("needs_review"):
            review_count += 1
            public_dates = [
                field
                for field in (
                    "registration_start",
                    "registration_end",
                    "competition_start",
                    "competition_end",
                )
                if item.get(field)
            ]
            if public_dates:
                errors.append(
                    "%s 待核验记录不应保留公开赛程字段: %s"
                    % (prefix, ", ".join(public_dates))
                )
        else:
            if not item.get("last_checked"):
                errors.append("%s 已核验记录缺少 last_checked" % prefix)
            if not link:
                errors.append("%s 已核验记录缺少赛事深链接" % prefix)
            if not item.get("status_override") and not any(
                item.get(field)
                for field in (
                    "registration_start",
                    "registration_end",
                    "competition_start",
                    "competition_end",
                )
            ):
                errors.append("%s 已核验记录缺少赛程或官方状态" % prefix)
            if item.get("active"):
                verified_active += 1

    if verified_active == 0:
        errors.append("至少需要一条已核验且启用的赛事")
    if review_count:
        warnings.append("%d 条记录仍标记为 needs_review" % review_count)

    return errors, warnings


def main():
    errors, warnings = validate()
    for warning in warnings:
        print("WARN: " + warning)
    for error in errors:
        print("ERROR: " + error, file=sys.stderr)
    if errors:
        print("数据校验失败: %d 个错误" % len(errors), file=sys.stderr)
        return 1
    print("数据校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

