# -*- coding: utf-8 -*-
"""在维护者本机或 ECS 上执行完整自动化流程（适合国内 IP + 校内通知 + 国际源）。

顺序：git pull → 各源采集 → AI 审核 → 自动发布 AI 通过项 → 预计报名推算 → 校验/测试闸门 → 自动提交推送。
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
    result = subprocess.Popen(
        ["git", "status", "--porcelain", "data/"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, _err = result.communicate()
    text = out.decode("utf-8", "replace") if isinstance(out, bytes) else (out or "")
    return bool(text.strip())


def main():
    parser = argparse.ArgumentParser(description="本机/ECS 完整同步流程")
    parser.add_argument("--skip", default="", help="跳过的源，逗号分隔，如 tianchi,kaggle")
    parser.add_argument("--no-pull", action="store_true", help="跳过 git pull")
    parser.add_argument("--no-push", action="store_true", help="只提交不推送")
    args = parser.parse_args()

    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    if not args.no_pull:
        run(["git", "pull", "--rebase"])

    results = {}
    for name, script in FETCHERS:
        if name in skip:
            print("跳过源: %s" % name)
            results[name] = "skipped"
            continue
        results[name] = "success" if run([PY, script]) == 0 else "failed"

    attempted = [r for r in results.values() if r != "skipped"]
    succeeded = [r for r in attempted if r == "success"]
    print("\n采集源结果: %s" % ", ".join("%s=%s" % kv for kv in results.items()))
    if attempted and not succeeded:
        print("全部 %d 个采集源均失败，已中止，不提交。" % len(attempted), file=sys.stderr)
        return 1
    if len(succeeded) < len(attempted):
        print("注意：%d 个源失败，本次同步质量为 partial。" % (len(attempted) - len(succeeded)))

    if run([PY, "scripts/review_drafts.py"]) != 0:
        print("审核脚本自身执行失败，已中止。", file=sys.stderr)
        return 1

    if run([PY, "scripts/auto_publish_queue.py"]) != 0:
        print("自动发布 AI 通过候选失败，已中止，不提交。", file=sys.stderr)
        return 1

    # 与 weekly-sync 一致：维护固定清单「预计报名」（无历史不臆造；禁假深链）
    if run([PY, "scripts/apply_registration_estimates.py"]) != 0:
        print("预计报名维护失败，已中止，不提交。", file=sys.stderr)
        return 1

    # degraded 外链预算（3%）：超预算先 demote，再进 validate
    if run([PY, "scripts/enforce_degraded_budget.py"]) != 0:
        print("degraded 预算强制失败，已中止，不提交。", file=sys.stderr)
        return 1

    # 闸门：不合规不提交
    if run([PY, "scripts/validate_data.py"]) != 0:
        print("数据校验未通过，已中止，不提交。", file=sys.stderr)
        return 1
    if run(["npm", "test"]) != 0:
        print("测试未通过，已中止，不提交。", file=sys.stderr)
        return 1

    # 与 GitHub weekly-sync 共用：标记本周已成功，备用 cron 可跳过
    os.environ.setdefault("SYNC_SOURCE", "local")
    for name, result in results.items():
        os.environ["SOURCE_%s" % name.upper()] = result
    run([PY, "scripts/write_sync_state.py"])

    if not data_changed():
        print("\n本次无数据变更，无需提交。")
        return 0

    run(["git", "add", "data/"])
    run(["git", "commit", "-m", "chore(data): auto sync & publish competitions"])
    if not args.no_push:
        run(["git", "push"])
    print("\n完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
