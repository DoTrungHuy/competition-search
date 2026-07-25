# -*- coding: utf-8 -*-
"""对 data/competitions.json 执行 degraded 链接预算（3% 上限）。

超预算时按优先级 demote 多余 degraded（清字段并清空 link），写回 JSON。
始终 exit 0（预算强制执行后数据应可过 validate 闸门）。
"""
from __future__ import print_function

import json
import os
import sys

import link_health


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPS_PATH = os.path.join(ROOT, "data", "competitions.json")


def main():
    with open(COMPS_PATH, "r", encoding="utf-8") as handle:
        doc = json.load(handle)

    competitions = doc.get("competitions") or []
    before = link_health.count_degraded(competitions)
    total = len(competitions)
    allowed = link_health.max_degraded_allowed(total)

    out, dropped = link_health.enforce_degraded_budget(competitions)
    after = link_health.count_degraded(out)

    doc["competitions"] = out
    with open(COMPS_PATH, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(
        "degraded budget: before=%d after=%d dropped=%d max=%d (total=%d)"
        % (before, after, len(dropped), allowed, total)
    )
    if dropped:
        for item in dropped:
            print(
                "  demoted: %s (%s)"
                % (item.get("id") or "?", item.get("name") or "")
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
