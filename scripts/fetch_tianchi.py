# -*- coding: utf-8 -*-
"""用 Playwright 无头浏览器抓取阿里云天池的竞赛列表，生成待审核草稿。

天池竞赛列表是前端渲染的 SPA，简单 HTTP 抓不到，需渲染后再抽取。
抽取依据稳定的 URL 规律：竞赛详情形如 /competition/entrance/<id>/...，
按此 pattern 收集链接与标题，不依赖易变的 CSS 类。

⚠️ 该脚本面向“在维护者本机运行”（国内 IP + 真实浏览器更易通过反爬），
不建议放到境外的 GitHub Actions runner。首次使用需：

    python -m pip install -r requirements-playwright.txt
    python -m playwright install chromium

本脚本不会写入 data/competitions.json。
"""
from __future__ import print_function

import argparse
import os
import re
import sys
from datetime import datetime

import json
import requests
from draft_common import ROOT, categorize, load_production, save_draft, stable_id
from platform_text import description_for, eligibility_for


DEFAULT_OUT = os.path.join(ROOT, "scripts", "out", "draft_tianchi.json")
ACTIVE_URL = "https://tianchi.aliyun.com/competition/activeList"
API_URL = "https://tianchi.aliyun.com/competition/proxy/api/competition/api/race/listBrief"
ENTRANCE_RE = re.compile(r"/competition/entrance/(\d+)")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def collect_via_api(timeout_ms=25000, max_pages=5):
    """优先调用天池公开 JSON 接口获取进行中竞赛及起止日期（免 Playwright）。"""
    events = {}
    timeout_sec = max(5, int(timeout_ms / 1000))
    for page_num in range(1, max_pages + 1):
        resp = requests.get(
            API_URL,
            params={"pageNum": page_num, "pageSize": 20, "state": 1},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=timeout_sec,
        )
        resp.raise_for_status()
        payload = resp.json()
        race_list = (payload.get("data") or {}).get("list") or []
        if not race_list:
            break
        for item in race_list:
            cid = str(item.get("raceId") or "").strip()
            name = str(item.get("raceName") or "").strip()
            if not cid or not name or cid in events:
                continue
            start_raw = str(item.get("currentSeasonStart") or "")[:10]
            end_raw = str(item.get("currentSeasonEnd") or "")[:10]
            brief = " ".join(str(item.get("brief") or "").split())
            events[cid] = {
                "id": cid,
                "name": name,
                "link": "https://tianchi.aliyun.com/competition/entrance/%s/introduction"
                % cid,
                "registration_start": start_raw if re.match(r"^\d{4}-\d{2}-\d{2}$", start_raw) else None,
                "registration_end": end_raw if re.match(r"^\d{4}-\d{2}-\d{2}$", end_raw) else None,
                "competition_start": start_raw if re.match(r"^\d{4}-\d{2}-\d{2}$", start_raw) else None,
                "competition_end": end_raw if re.match(r"^\d{4}-\d{2}-\d{2}$", end_raw) else None,
                "brief": brief[:240] if brief else None,
            }
        total = (payload.get("data") or {}).get("total") or 0
        if page_num * 20 >= total:
            break
    return list(events.values())


def collect(url, headed, timeout_ms, scrolls, wait_ms):
    """渲染页面并抽取 {id: {name, link}}。缺少 Playwright 时抛 RuntimeError。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "未安装 Playwright。请先执行:\n"
            "  python -m pip install -r requirements-playwright.txt\n"
            "  python -m playwright install chromium"
        )

    anchors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        context = browser.new_context(user_agent=USER_AGENT, locale="zh-CN")
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        for _ in range(max(0, scrolls)):
            page.mouse.wheel(0, 20000)
            page.wait_for_timeout(wait_ms)
        anchors = page.eval_on_selector_all(
            "a[href*='/competition/entrance/']",
            "els => els.map(e => ({href: e.href, text: (e.innerText||'').trim()}))",
        )
        browser.close()

    events = {}
    for anchor in anchors:
        match = ENTRANCE_RE.search(anchor.get("href") or "")
        if not match:
            continue
        cid = match.group(1)
        text = anchor.get("text") or ""
        name = next((line.strip() for line in text.splitlines() if line.strip()), "")
        if not name or cid in events:
            continue
        events[cid] = {
            "id": cid,
            "name": name,
            "link": "https://tianchi.aliyun.com/competition/entrance/%s/introduction"
            % cid,
        }
    return list(events.values())


def to_draft_record(event):
    record = {
        "id": stable_id("tianchi", event["link"]),
        "brand_id": "tianchi",
        "edition": str(datetime.now().year),
        "track_id": "tianchi-%s" % event["id"],
        "name": event["name"],
        "kind": "大厂赛事",
        "info_channel": "官方渠道",
        "link": event["link"],
        "active": True,
        "last_checked": None,
        "needs_review": True,
        "draft": True,
        "source_list": "tianchi",
        "source_list_name": "阿里云天池",
    }
    for field in (
        "registration_start",
        "registration_end",
        "competition_start",
        "competition_end",
    ):
        if event.get(field):
            record[field] = event[field]
    record["eligibility"] = eligibility_for(record, "tianchi")
    record["description"] = event.get("brief") or description_for(record, "tianchi")
    return record


def main():
    parser = argparse.ArgumentParser(description="抓取天池竞赛草稿（优先公开 JSON API，回退 Playwright）")
    parser.add_argument("--out", default=DEFAULT_OUT, help="输出草稿 JSON 路径")
    parser.add_argument("--url", default=ACTIVE_URL, help="列表页地址")
    parser.add_argument("--headed", action="store_true", help="显示浏览器（调试/过反爬）")
    parser.add_argument("--scrolls", type=int, default=6, help="滚动加载次数")
    parser.add_argument("--timeout", type=int, default=45000, help="打开超时毫秒")
    parser.add_argument("--wait", type=int, default=1500, help="每次滚动等待毫秒")
    args = parser.parse_args()

    errors = []
    accepted = []
    try:
        events = collect_via_api(timeout_ms=args.timeout)
        if not events:
            events = collect(args.url, args.headed, args.timeout, args.scrolls, args.wait)
        print("抽到 %d 个竞赛" % len(events))
        accepted = [to_draft_record(event) for event in events]
    except RuntimeError as error:
        print("失败: %s" % error, file=sys.stderr)
        errors.append(str(error))
    except Exception as error:  # API / Playwright 超时或反爬错误
        message = "%s -> %s" % (args.url, error)
        print("失败: %s" % message, file=sys.stderr)
        errors.append(message)

    categorized = categorize(accepted, [], load_production())
    counts = save_draft(args.out, "tianchi.aliyun.com", categorized, errors)
    print(
        "完成: 新增 {new} / 变更 {changed} / 重复 {duplicate} / 拒绝 {rejected}".format(
            **counts
        )
    )
    print("草稿: %s" % args.out)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
