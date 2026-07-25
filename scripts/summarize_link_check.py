# -*- coding: utf-8 -*-
"""把 check_links.py 的报告转成 Markdown 摘要，供 GitHub job summary 展示。

reports/ 是 gitignore 的本地产物，跑完就随 runner 销毁；不做摘要的话，
周更里的链接巡检结果没人看得到，等于白跑。

只读不写，永远以 0 退出：这是报告工具，不该成为流水线的失败点。
"""
from __future__ import print_function

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REPORT = os.path.join(ROOT, "reports", "link-check.json")

# 这些分类意味着链接可能真的坏了，值得人工看一眼。
# anti_bot / timeout / network_error 多是对方反爬或抖动，不单独点名。
ACTIONABLE = ("broken", "http_error", "certificate_error")
MAX_LISTED = 20


def render(report):
    lines = ["### 外链巡检", ""]
    counts = report.get("classifications") or {}
    lines.append("共 %d 条。" % report.get("count", 0))
    lines.append("")
    if counts:
        lines.append("| 分类 | 数量 |")
        lines.append("| --- | --- |")
        for key in sorted(counts):
            lines.append("| %s | %d |" % (key, counts[key]))
        lines.append("")

    broken = [
        item
        for item in report.get("results", [])
        if item.get("classification") in ACTIONABLE
    ]
    if not broken:
        lines.append("没有需要人工处理的链接。")
        return lines

    lines.append("**需要人工处理：**")
    lines.append("")
    for item in broken[:MAX_LISTED]:
        lines.append(
            "- `%s` — %s" % (item.get("url"), item.get("classification"))
        )
    if len(broken) > MAX_LISTED:
        lines.append("- ……另有 %d 条，详见 reports/link-check.json" % (len(broken) - MAX_LISTED))
    return lines


def main():
    parser = argparse.ArgumentParser(description="输出链接巡检的 Markdown 摘要")
    parser.add_argument("--report", default=DEFAULT_REPORT)
    args = parser.parse_args()

    if not os.path.exists(args.report):
        print("### 外链巡检")
        print()
        print("未生成报告（巡检步骤失败或被跳过）。")
        return 0

    try:
        with open(args.report, "r", encoding="utf-8") as handle:
            report = json.load(handle)
    except (ValueError, OSError) as error:
        print("### 外链巡检")
        print()
        print("报告无法解析：%s" % error)
        return 0

    for line in render(report):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
