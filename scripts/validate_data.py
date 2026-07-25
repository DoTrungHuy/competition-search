# -*- coding: utf-8 -*-
"""校验生产赛事、品牌和平台入口数据。"""
from __future__ import print_function

import json
import os
import sys
from datetime import date, datetime, timedelta
from urllib.parse import urlparse


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import link_integrity  # noqa: E402
import link_health  # noqa: E402

DATA_DIR = os.path.join(ROOT, "data")
DATE_FIELDS = (
    "registration_start",
    "registration_end",
    "registration_start_estimated",
    "registration_end_estimated",
    "competition_start",
    "competition_end",
    "published_at",
    "last_checked",
    "status_override_until",
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
# 终态覆盖是稳定事实，长期有效；其余为动态状态，必须能判断新鲜度。
TERMINAL_STATUS_OVERRIDES = {"已结束", "已停办", "报名结束"}
# 与 js/status.js 的 STATUS_OVERRIDE_MAX_DAYS 保持一致。
STATUS_OVERRIDE_MAX_DAYS = 90

# 采集/合并时禁止再写入的纯套话（列表「要求」不得全站同一句）
GENERIC_ELIGIBILITY = {
    "以活动页面为准",
    "以赛题页面为准",
    "以通知原文为准",
    "open",
    "详见官网",
    "见官网详情",
}
GENERIC_DESCRIPTIONS = {
    "MLH 认证的国际黑客松，报名与规则以活动页面为准。",
    "Devpost 平台国际黑客松，报名与规则以活动页面为准。",
    "阿里云天池平台竞赛，报名与规则以赛题页面为准。",
    "Kaggle 平台数据科学竞赛，报名与规则以赛题页面为准。",
}
PLATFORM_BRANDS = {"mlh", "devpost", "tianchi", "kaggle"}


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


def parse_date(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def override_expiry(item):
    """覆盖状态的有效截止日：显式 status_override_until 优先，否则 last_checked + 90 天。

    与 js/status.js 的 overrideExpiry 保持一致。
    """
    explicit = parse_date(item.get("status_override_until"))
    if explicit:
        return explicit
    checked = parse_date(item.get("last_checked"))
    if not checked:
        return None
    return checked + timedelta(days=STATUS_OVERRIDE_MAX_DAYS)


def valid_url(value):
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def normalized_url(value):
    return str(value or "").rstrip("/")


def validate(today=None):
    TODAY = today or date.today()
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
            item.get("registration_start_estimated")
            and item.get("registration_end_estimated")
            and item["registration_start_estimated"]
            > item["registration_end_estimated"]
        ):
            errors.append("%s 预计报名开始晚于预计报名截止" % prefix)
        if (
            item.get("competition_start")
            and item.get("competition_end")
            and item["competition_start"] > item["competition_end"]
        ):
            errors.append("%s 比赛开始晚于比赛结束" % prefix)

        has_official_reg = bool(
            item.get("registration_start") or item.get("registration_end")
        )
        has_estimated_reg = bool(
            item.get("registration_start_estimated")
            or item.get("registration_end_estimated")
        )
        if has_estimated_reg:
            if item.get("schedule_source") not in (None, "estimated", "official"):
                errors.append(
                    "%s schedule_source 非法: %s"
                    % (prefix, item.get("schedule_source"))
                )
            if has_official_reg and item.get("schedule_source") == "estimated":
                errors.append(
                    "%s 已有官方报名日时不应再标 schedule_source=estimated" % prefix
                )
            if item.get("needs_review") is True:
                errors.append("%s 待核验记录不应带预计报名日" % prefix)

        link = item.get("link")
        link_kind = item.get("link_kind")
        is_estimate = link_integrity.is_estimate_record(item)
        # 硬门禁：伪参数 / 预计深链 / 缺 brand_home 一律失败（不可绕过）
        errors.extend(
            link_integrity.check_competition_link_honesty(
                item, brand, prefix=prefix
            )
        )
        errors.extend(link_health.degraded_field_errors(item, prefix=prefix))
        if link and not is_estimate:
            if not valid_url(link):
                errors.append("%s link 非法" % prefix)
            if normalized_url(link) == normalized_url(brand.get("official_home")):
                errors.append("%s link 不能与品牌首页相同" % prefix)
            if link in event_links:
                errors.append("赛事深链接重复: %s" % link)
            event_links.add(link)

        override = item.get("status_override")
        if override and override not in STATUS_OVERRIDES:
            errors.append("%s status_override 非法" % prefix)

        # 动态状态覆盖必须能判断新鲜度，否则会永久谎报「现在能报名」。
        # 前端已能自愈（过期即回落到日期推导或待复核），故这里只在数据自相矛盾时报错，
        # 单纯「已过期」只告警——避免一条陈旧数据让周一无人值守的流水线整体中断。
        until_raw = item.get("status_override_until")
        if until_raw and not override:
            errors.append("%s 有 status_override_until 却没有 status_override" % prefix)
        until = parse_date(until_raw)
        checked = parse_date(item.get("last_checked"))
        if until and checked and until < checked:
            errors.append(
                "%s status_override_until (%s) 早于 last_checked (%s)"
                % (prefix, until_raw, item.get("last_checked"))
            )
        if override and override not in TERMINAL_STATUS_OVERRIDES:
            expiry = override_expiry(item)
            if expiry is None:
                errors.append(
                    "%s status_override「%s」是动态状态，须有 last_checked 或 status_override_until"
                    % (prefix, override)
                )
            elif expiry < TODAY:
                warnings.append(
                    "%s status_override「%s」已于 %s 过期，前端将回落为待复核，请复核后更新"
                    % (prefix, override, expiry.isoformat())
                )

        eligibility = item.get("eligibility")
        if isinstance(eligibility, str) and eligibility.strip() in GENERIC_ELIGIBILITY:
            errors.append(
                "%s eligibility 不能是纯套话「%s」，须区分到具体赛事"
                % (prefix, eligibility.strip())
            )
        description = item.get("description")
        if (
            item.get("brand_id") in PLATFORM_BRANDS
            and isinstance(description, str)
            and description.strip() in GENERIC_DESCRIPTIONS
        ):
            errors.append(
                "%s description 不能使用平台统一模板，须带上赛事名" % prefix
            )

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
            if is_estimate:
                # official_home / link_kind 已由 link_integrity 强制
                pass
            elif not link:
                errors.append("%s 已核验记录缺少赛事深链接" % prefix)
            if not item.get("status_override") and not any(
                item.get(field)
                for field in (
                    "registration_start",
                    "registration_end",
                    "registration_start_estimated",
                    "registration_end_estimated",
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

    errors.extend(link_health.budget_errors(competitions.get("competitions", [])))

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

