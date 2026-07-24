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


def main():
    sh = timezone(timedelta(hours=8))
    now = datetime.now(sh)
    week = os.environ.get("THIS_WEEK") or now.strftime("%G-W%V")
    state = {
        "last_success_week": week,
        "last_success_at": now.isoformat(timespec="seconds"),
        "source": os.environ.get("SYNC_SOURCE") or "github-actions",
        "run_url": os.environ.get("RUN_URL") or "",
        "event": os.environ.get("GITHUB_EVENT_NAME") or "",
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
