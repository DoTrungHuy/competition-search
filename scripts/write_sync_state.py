# -*- coding: utf-8 -*-
"""写入 data/sync_state.json，供 weekly-sync 备用时段做「本周已成功」守卫。"""
from __future__ import print_function

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "sync_state.json"

# 采集源 -> 传入结果的环境变量名。值取 success / failed / skipped。
# 只记录本次实际报告过的源：CI 跑 4 个，本地 run_local_sync 多跑 tianchi，
# 各自如实记录，不给没跑的源留占位噪声。
SOURCE_ENV = (
    ("campus", "SOURCE_CAMPUS"),
    ("devpost", "SOURCE_DEVPOST"),
    ("mlh", "SOURCE_MLH"),
    ("kaggle", "SOURCE_KAGGLE"),
    ("tianchi", "SOURCE_TIANCHI"),
)
VALID_RESULTS = ("success", "failed", "skipped")


def collect_sources():
    sources = {}
    for name, env_key in SOURCE_ENV:
        value = (os.environ.get(env_key) or "").strip().lower()
        if not value:
            continue
        sources[name] = value if value in VALID_RESULTS else "failed"
    return sources


def sync_quality(sources):
    """全绿为 ok；有失败但至少一个成功为 partial。全失败不该走到这里（调用方已拦截）。"""
    if not sources:
        return "unknown"
    attempted = [v for v in sources.values() if v != "skipped"]
    if not attempted:
        return "skipped"
    if all(v == "success" for v in attempted):
        return "ok"
    if any(v == "success" for v in attempted):
        return "partial"
    return "failed"


def main():
    sh = timezone(timedelta(hours=8))
    now = datetime.now(sh)
    week = os.environ.get("THIS_WEEK") or now.strftime("%G-W%V")
    sources = collect_sources()
    state = {
        "last_success_week": week,
        "last_success_at": now.isoformat(timespec="seconds"),
        "source": os.environ.get("SYNC_SOURCE") or "github-actions",
        "run_url": os.environ.get("RUN_URL") or "",
        "event": os.environ.get("GITHUB_EVENT_NAME") or "",
        "sources": sources,
        "sync_quality": sync_quality(sources),
    }
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote", STATE_PATH)
    print(json.dumps(state, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
