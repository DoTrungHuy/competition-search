# -*- coding: utf-8 -*-
"""平台赛事（MLH / Devpost / 天池 / Kaggle）的要求与简介文案。

采集侧禁止再写统一的「以活动页面为准」；每条至少带上赛事名，
有主办方时再带上主办方，保证列表「要求」字段彼此可区分。
"""
from __future__ import print_function


PLATFORM_BRANDS = frozenset({"mlh", "devpost", "tianchi", "kaggle"})

# 只剩套话、没有任何赛事区分信息的要求文案（公开页不得原样保留）。
GENERIC_ELIGIBILITY = frozenset(
    {
        "以活动页面为准",
        "以赛题页面为准",
        "以通知原文为准",
        "open",
        "详见官网",
        "见官网详情",
    }
)

# 历史采集留下的完全相同简介。
GENERIC_DESCRIPTIONS = frozenset(
    {
        "MLH 认证的国际黑客松，报名与规则以活动页面为准。",
        "Devpost 平台国际黑客松，报名与规则以活动页面为准。",
        "阿里云天池平台竞赛，报名与规则以赛题页面为准。",
        "Kaggle 平台数据科学竞赛，报名与规则以赛题页面为准。",
    }
)


def clean_text(value):
    return " ".join(str(value or "").split())


def event_name(record):
    return clean_text(record.get("name")) or "该赛事"


def event_org(record):
    return clean_text(record.get("organizer"))


def is_generic_eligibility(value):
    text = clean_text(value)
    return not text or text in GENERIC_ELIGIBILITY


def is_generic_description(value):
    text = clean_text(value)
    return not text or text in GENERIC_DESCRIPTIONS


def resolve_brand(record, brand_id=None):
    return clean_text(
        brand_id or record.get("brand_id") or record.get("source_list") or ""
    )


def eligibility_for(record, brand_id=None):
    """生成短「要求」行：可一眼区分赛事，并保留「以官网为准」的提示。"""
    brand = resolve_brand(record, brand_id)
    name = event_name(record)
    org = event_org(record)
    edition = clean_text(record.get("edition"))

    if brand == "mlh":
        if edition.isdigit():
            return "MLH %s 赛季「%s」；对象与组队见活动页" % (edition, name)
        return "MLH 认证「%s」；对象与组队见活动页" % name
    if brand == "devpost":
        if org:
            return "「%s」由 %s 主办；资格与组队见活动页" % (name, org)
        return "Devpost「%s」；资格与组队见活动页" % name
    if brand == "tianchi":
        return "天池「%s」；对象与规则见赛题页" % name
    if brand == "kaggle":
        if org:
            return "Kaggle「%s」/ %s；资格见赛题页" % (name, org)
        return "Kaggle「%s」；资格与规则见赛题页" % name
    if org:
        return "%s 相关；规则以官方原文为准" % org
    return "「%s」规则以官方原文为准" % name


def description_for(record, brand_id=None):
    """生成简介：以赛事名开头，可附带主办方与平台身份。"""
    brand = resolve_brand(record, brand_id)
    name = event_name(record)
    org = event_org(record)
    edition = clean_text(record.get("edition"))

    if brand == "mlh":
        if edition.isdigit():
            return (
                "%s 为 MLH %s 赛季认证黑客松。报名、赛程与规则以活动页为准。"
                % (name, edition)
            )
        return "%s 为 MLH 认证黑客松。报名、赛程与规则以活动页为准。" % name
    if brand == "devpost":
        if org:
            return (
                "%s，由 %s 在 Devpost 发起的在线黑客松。报名与规则以活动页为准。"
                % (name, org)
            )
        return "%s 为 Devpost 在线黑客松。报名、赛程与规则以活动页为准。" % name
    if brand == "tianchi":
        return "%s 为阿里云天池平台竞赛。报名对象、赛制与规则以赛题页为准。" % name
    if brand == "kaggle":
        if org:
            return "%s 为 Kaggle 竞赛（主办：%s）。资格与规则以赛题页为准。" % (
                name,
                org,
            )
        return "%s 为 Kaggle 数据科学竞赛。资格与规则以赛题页为准。" % name
    return "%s。规则与时间以官方原文为准。" % name


def enrich_platform_text(record, brand_id=None, force=False):
    """补齐/重写平台赛事文案。返回是否发生修改。"""
    brand = resolve_brand(record, brand_id)
    if brand not in PLATFORM_BRANDS:
        return False

    changed = False
    if force or is_generic_eligibility(record.get("eligibility")):
        new_value = eligibility_for(record, brand)
        if record.get("eligibility") != new_value:
            record["eligibility"] = new_value
            changed = True
    if force or is_generic_description(record.get("description")):
        new_value = description_for(record, brand)
        if record.get("description") != new_value:
            record["description"] = new_value
            changed = True
    return changed
