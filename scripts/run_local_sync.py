# -*- coding: utf-8 -*-
"""在维护者本机执行完整自动化流程（适合国内 IP + 天池等需渲染的源）。

顺序：git pull → 各源采集 → DeepSeek 审核 → 合并 → 校验/测试闸门 → 自动提交推送。

单个采集源失败不中断整体；但数据校验或测试不通过则中断、绝不提交。
配合 Windows 任务计划程序即可每周自动运行。需环境变量 DEEPSEEK_API_KEY，
天池源需先安装 Playwright（见 requirements-playwright.txt）。
"""
from __future__ import print_function

import argparse
import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

# (名称, 脚本相对路径) —— 名称用于 --skip 过滤。
FETCHERS = [
    ("campus", "scripts/fetch_campus_cxcy.py"),
    ("devpost", "scripts/fetch_devpost.py"),
    ("mlh", "scripts/fetch_mlh.py"),
    ("kaggle", "scripts/fetch_kaggle.py"),
    ("tianchi", "scripts/fetch_tianchi.py"),
]


def run(cmd, check=False):
    print("\n>> " + " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT).returncode


def data_changed():
    result = subprocess.run(
        ["git", "status", "--porcelain", "data/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(description="本机完整同步流程")
    parser.add_argument("--skip", default="", help="跳过的源，逗号分隔，如 tianchi,kaggle")
    parser.add_argument("--no-pull", action="store_true", help="跳过 git pull")
    parser.add_argument("--no-push", action="store_true", help="只提交不推送")
    args = parser.parse_args()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("缺少环境变量 DEEPSEEK_API_KEY", file=sys.stderr)
        return 2

    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    if not args.no_pull:
        run(["git", "pull", "--rebase"])

    for name, script in FETCHERS:
        if name in skip:
            print("跳过源: %s" % name)
            continue
        run([PY, script])  # 单源失败不中断

    if run([PY, "scripts/review_drafts.py"]) == 2:
        print("审核无法进行（缺 key），中止。", file=sys.stderr)
        return 2

    run([PY, "scripts/apply_reviewed.py"])

    # 闸门：不合规不提交
    if run([PY, "scripts/validate_data.py"]) != 0:
        print("数据校验未通过，已中止，不提交。", file=sys.stderr)
        return 1
    if run(["npm", "test"]) != 0:
        print("测试未通过，已中止，不提交。", file=sys.stderr)
        return 1

    if not data_changed():
        print("\n本次无数据变更，无需提交。")
        return 0

    run(["git", "add", "data/"])
    run(["git", "commit", "-m", "chore(data): local auto-sync reviewed competitions"])
    if not args.no_push:
        run(["git", "push"])
    print("\n完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
