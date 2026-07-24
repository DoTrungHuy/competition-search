# -*- coding: utf-8 -*-
"""
链接诚信：禁止生产数据出现伪报名深链 / 往届深链冒充本届。

任何写入预计记录、以及 validate_data / npm test 都必须走这里。
规则一旦放宽，等于再次允许「打不开的假信息」。
"""
from __future__ import print_function

import re
from urllib.parse import parse_qs, urlparse


# 伪参数、伪造路径——出现即视为不可信 URL
FAKE_QUERY_KEYS = ("estimate", "estimated", "fake", "projected")
FAKE_PATH_MARKERS = (
    "/estimate/",
    "/estimated/",
    "estimate=",
)


def is_estimate_record(item):
    if not isinstance(item, dict):
        return False
    if item.get("schedule_source") == "estimated":
        return True
    if item.get("link_kind") == "brand_home":
        return True
    if str(item.get("id") or "").startswith("estimate-"):
        return True
    if item.get("registration_start_estimated") or item.get(
        "registration_end_estimated"
    ):
        return True
    return False


def url_has_fake_markers(url):
    """检测 ?estimate=、路径 /estimate/ 等伪造痕迹。"""
    if not isinstance(url, str) or not url.strip():
        return False
    raw = url.strip()
    lower = raw.lower()
    for marker in FAKE_PATH_MARKERS:
        if marker in lower:
            return True
    try:
        parsed = urlparse(raw)
    except Exception:
        return True
    query = parse_qs(parsed.query, keep_blank_values=True)
    for key in query:
        if str(key).lower() in FAKE_QUERY_KEYS:
            return True
    # 宽松兜底：未解析出 query 时仍匹配 estimate=
    if re.search(r"[?&#]estimate(d)?=", lower):
        return True
    return False


def check_competition_link_honesty(item, brand=None, prefix=None):
    """
    返回错误字符串列表（空 = 通过）。
    brand: 可选 dict，需含 official_home。
    """
    errors = []
    prefix = prefix or ("competitions[%s]" % (item.get("id") or "?"))
    brand = brand or {}
    link = item.get("link")
    link_kind = item.get("link_kind")
    estimate = is_estimate_record(item)

    if link_kind is not None and link_kind not in (None, "event", "brand_home"):
        errors.append("%s link_kind 非法: %s" % (prefix, link_kind))

    if isinstance(link, str) and url_has_fake_markers(link):
        errors.append(
            "%s link 含伪参数/伪路径（如 estimate=），禁止写入生产数据: %s"
            % (prefix, link)
        )

    if estimate:
        if link:
            errors.append(
                "%s 预计/品牌主页类记录禁止填写赛事深链接 link（须留空，"
                "前端仅使用品牌 official_home）"
                % prefix
            )
        if link_kind != "brand_home":
            errors.append("%s 预计记录须标记 link_kind=brand_home" % prefix)
        home = (brand.get("official_home") or "").strip()
        if not home:
            errors.append("%s 预计记录所属品牌缺少 official_home" % prefix)
        if isinstance(home, str) and url_has_fake_markers(home):
            errors.append("%s 品牌 official_home 含伪参数，不可用于预计入口" % prefix)
    else:
        if link_kind == "brand_home":
            # 非预计却标 brand_home：仍禁止深链冒充
            if link:
                errors.append(
                    "%s link_kind=brand_home 时不应再填赛事深链接" % prefix
                )

    return errors


def audit_collections(competitions, brands_by_id):
    """对整表 competitions 做链接诚信审计。"""
    errors = []
    for index, item in enumerate(competitions or []):
        bid = item.get("brand_id")
        brand = brands_by_id.get(bid) or {}
        prefix = "competitions[%d]" % index
        if item.get("id"):
            prefix = "%s(%s)" % (prefix, item.get("id"))
        errors.extend(check_competition_link_honesty(item, brand, prefix))
    return errors
