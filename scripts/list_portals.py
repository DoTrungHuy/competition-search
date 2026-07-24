# -*- coding: utf-8 -*-
"""从 sources.yaml 打印官方入口清单，供人工巡查。"""
from __future__ import print_function

import sys

from source_config import SourceConfigError, load_sources


def main():
    try:
        portals = load_sources()["portals"]
    except SourceConfigError as error:
        print("配置错误: %s" % error, file=sys.stderr)
        return 1

    print("各比赛与渠道入口（人工打开核对）\n")
    print("%-18s %-12s %-24s %s" % ("id", "kind", "name", "url"))
    print("-" * 100)
    for portal in portals:
        print(
            "%-18s %-12s %-24s %s"
            % (portal["id"], portal["kind"], portal["name"], portal["url"])
        )
    print("\n校内通知草稿: python scripts/fetch_campus_cxcy.py")
    print("链接巡检: python scripts/check_links.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

