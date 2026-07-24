# -*- coding: utf-8 -*-
"""读取并校验 scripts/sources.yaml。"""
from __future__ import print_function

import os

import yaml


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(ROOT, "scripts", "sources.yaml")


class SourceConfigError(ValueError):
    pass


def load_sources(path=DEFAULT_PATH):
    if not os.path.isfile(path):
        raise SourceConfigError("找不到采集配置: %s" % path)
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise SourceConfigError("sources.yaml 顶层必须是对象")

    campus = data.get("campus")
    portals = data.get("portals")
    if not isinstance(campus, dict):
        raise SourceConfigError("sources.yaml 缺少 campus")
    if not isinstance(portals, list):
        raise SourceConfigError("sources.yaml 缺少 portals")

    for field in ("base", "user_agent", "lists", "selectors"):
        if not campus.get(field):
            raise SourceConfigError("campus 缺少字段: %s" % field)
    for field in ("item", "link", "date"):
        if not campus["selectors"].get(field):
            raise SourceConfigError("campus.selectors 缺少字段: %s" % field)

    portal_ids = set()
    for index, portal in enumerate(portals):
        for field in ("id", "name", "kind", "url"):
            if not portal.get(field):
                raise SourceConfigError("portals[%d] 缺少字段: %s" % (index, field))
        if portal["id"] in portal_ids:
            raise SourceConfigError("portal id 重复: %s" % portal["id"])
        portal_ids.add(portal["id"])
    return data

