# -*- coding: utf-8 -*-
"""
外链健康：degraded 链接公告预算（3% 上限）与字段校验。

超预算时按优先级保留部分 degraded，其余清除 link_status 相关字段并清空 link，
不删除赛事记录本身。
"""
from __future__ import print_function

import math


DEGRADED = "degraded"
OK = "ok"
ALLOWED_STATUS = (OK, DEGRADED)

# 国内 kind 优先于国际/平台赛
_DOMESTIC_KINDS = frozenset(
    (
        "全国赛事",
        "省级赛事",
        "校级赛事",
        "行业赛事",
        "企业赛事",
        "其他赛事",
    )
)
_LOW_BRAND_IDS = frozenset(("mlh", "devpost", "kaggle"))
_INTL_KINDS = frozenset(("国际赛事", "海外赛事"))

_STATUS_FIELDS = (
    "link_status",
    "link_status_reason",
    "link_status_checked_at",
)


def max_degraded_allowed(total):
    """允许的 degraded 数量上限：floor(total * 0.03)。"""
    if total is None or total < 0:
        total = 0
    return int(math.floor(int(total) * 0.03))


def count_degraded(competitions):
    """统计 link_status == degraded 的条数。"""
    n = 0
    for item in competitions or []:
        if isinstance(item, dict) and item.get("link_status") == DEGRADED:
            n += 1
    return n


def _is_low_priority_platform(item):
    brand = str(item.get("brand_id") or "").strip().lower()
    if brand in _LOW_BRAND_IDS:
        return True
    kind = str(item.get("kind") or "").strip()
    if kind in _INTL_KINDS:
        return True
    return False


def _is_domestic_kind(item):
    kind = str(item.get("kind") or "").strip()
    return kind in _DOMESTIC_KINDS


def degraded_priority_key(item):
    """
    排序键：越小越优先保留。
    1) has_campus_notice
    2) 国内 kind
    3) 国际 / mlh / devpost / kaggle 等低优先
    同档按 id 稳定排序。
    """
    if not isinstance(item, dict):
        return (9, "", "")
    campus = 0 if item.get("has_campus_notice") else 1
    if campus == 0:
        tier = 0
    elif _is_domestic_kind(item):
        tier = 1
    elif _is_low_priority_platform(item):
        tier = 3
    else:
        tier = 2
    cid = str(item.get("id") or "")
    return (campus, tier, cid)


def _clear_degraded_fields(item):
    """就地清除 degraded 字段并清空 link；返回被改动的副本引用。"""
    for key in _STATUS_FIELDS:
        if key in item:
            item[key] = None
        else:
            item[key] = None
    item["link"] = None
    return item


def enforce_degraded_budget(competitions):
    """
    若 degraded 超预算，保留高优先级条目，其余清除 status 字段与 link。
    不删除赛事。返回 (comps, dropped_list)。
    """
    if not competitions:
        return list(competitions or []), []

    # 浅拷贝列表与 dict，避免静默改写调用方未预期的共享对象
    comps = [dict(c) if isinstance(c, dict) else c for c in competitions]
    total = len(comps)
    allowed = max_degraded_allowed(total)
    degraded_idxs = [
        i
        for i, c in enumerate(comps)
        if isinstance(c, dict) and c.get("link_status") == DEGRADED
    ]
    # floor(n*0.03)==0 时无法表达“至少保留”的阈值，不强制挤掉
    # （与 test_under_budget_unchanged 一致：小样本不 demote）
    if allowed <= 0 or len(degraded_idxs) <= allowed:
        return comps, []

    # 高优先级在前；保留前 allowed 个，其余清除
    ranked = sorted(degraded_idxs, key=lambda i: degraded_priority_key(comps[i]))
    keep_set = set(ranked[:allowed])
    drop_idxs = [i for i in ranked if i not in keep_set]

    dropped = []
    for i in drop_idxs:
        cleared = _clear_degraded_fields(comps[i])
        dropped.append(cleared)

    return comps, dropped


def degraded_field_errors(item, prefix=None):
    """
    校验单条 competition 的 link_status 相关字段。
    返回错误字符串列表（空 = 通过）。
    """
    errors = []
    if not isinstance(item, dict):
        return errors
    prefix = prefix or ("competitions[%s]" % (item.get("id") or "?"))
    status = item.get("link_status")

    if status is None:
        return errors

    if status not in ALLOWED_STATUS:
        errors.append("%s link_status 非法: %s" % (prefix, status))
        return errors

    if status != DEGRADED:
        return errors

    reason = item.get("link_status_reason")
    if not (isinstance(reason, str) and reason.strip()):
        errors.append("%s degraded 缺少 link_status_reason" % prefix)

    checked = item.get("link_status_checked_at")
    if not (isinstance(checked, str) and checked.strip()):
        errors.append("%s degraded 缺少 link_status_checked_at" % prefix)

    return errors


def budget_errors(competitions, prefix="competitions"):
    """
    若 degraded 数量超过 3% 预算，返回错误列表（供后续 validate 使用）。
    """
    competitions = competitions or []
    total = len(competitions)
    degraded = count_degraded(competitions)
    allowed = max_degraded_allowed(total)
    if degraded > allowed:
        return [
            "%s degraded 超预算: %d/%d (上限 %d = floor(n*0.03))"
            % (prefix, degraded, total, allowed)
        ]
    return []
