# -*- coding: utf-8 -*-
"""【维护工具 / 手动】补审已入库的 needs_review 条目。

- 性质：维护者本机（或需要时）手动运行，不接入 GitHub Actions 周更。
- 作用：源日期优先，否则 DeepSeek 补充；仍无明确日期则保持待核验。
- 范围：只升级已有记录，不新增赛事；也不替代 weekly-sync / run_local_sync。

用法：

    python scripts/upgrade_pending.py
    python scripts/upgrade_pending.py --dry-run
    python scripts/upgrade_pending.py --limit 20
    python scripts/upgrade_pending.py --skip-model   # 只做源侧解析（Devpost/Kaggle 重抓）

需 DEEPSEEK_API_KEY 才会走模型补日期（可用 --skip-model 跳过）。
"""
from __future__ import print_function

import argparse
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

import requests

from schedule_utils import (
    SCHEDULE_FIELDS,
    can_auto_verify,
    clean_schedule,
    has_usable_schedule,
    parse_english_range,
    schedule_from_source_record,
    today_iso,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPETITIONS_PATH = os.path.join(ROOT, "data", "competitions.json")
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
USER_AGENT = "Mozilla/5.0 (compatible; CompetitionSearchMaintainer/0.1)"


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def norm_link(url):
    if not url:
        return ""
    parsed = urlparse(str(url).strip())
    host = (parsed.netloc or "").lower().replace("www.", "")
    path = (parsed.path or "").rstrip("/")
    return host + path


def fetch_devpost_schedule_map(pages=5, timeout=25, delay=0.6):
    """link_norm -> {source_schedule_text, raw fields}"""
    api = "https://devpost.com/api/hackathons"
    mapping = {}
    for page in range(1, pages + 1):
        params = [
            ("challenge_type[]", "online"),
            ("status[]", "open"),
            ("status[]", "upcoming"),
            ("status[]", "closed"),
            ("order_by", "recently-added"),
            ("page", str(page)),
        ]
        try:
            response = requests.get(
                api, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout
            )
            response.raise_for_status()
            batch = response.json().get("hackathons") or []
        except (requests.RequestException, ValueError, KeyError) as error:
            print("Devpost 抓取失败 page=%s: %s" % (page, error), file=sys.stderr)
            break
        if not batch:
            break
        for item in batch:
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            period = str(item.get("submission_period_dates") or "").strip() or None
            mapping[norm_link(url)] = {
                "source_schedule_text": period,
                "raw_schedule": {
                    "submission_period_dates": period,
                    "open_state": item.get("open_state"),
                    "time_left": item.get("time_left"),
                },
                "name": item.get("title"),
            }
        time.sleep(max(0.0, delay))
    print("Devpost 线索: %d 条" % len(mapping))
    return mapping


def fetch_kaggle_schedule_map(pages=3, timeout=25, delay=0.6):
    username = os.environ.get("KAGGLE_USERNAME")
    key = os.environ.get("KAGGLE_KEY")
    if not username or not key:
        print("跳过 Kaggle 重抓：未配置密钥")
        return {}
    api = "https://www.kaggle.com/api/v1/competitions/list"
    mapping = {}
    auth = (username, key)
    for page in range(1, pages + 1):
        try:
            response = requests.get(
                api,
                params={"page": page},
                auth=auth,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
            )
            response.raise_for_status()
            batch = response.json()
            if not isinstance(batch, list):
                batch = []
        except (requests.RequestException, ValueError) as error:
            print("Kaggle 抓取失败 page=%s: %s" % (page, error), file=sys.stderr)
            break
        if not batch:
            break
        for item in batch:
            ref = str(item.get("ref") or "").rstrip("/").split("/")[-1]
            url = str(item.get("url") or "").strip()
            if not url and ref:
                url = "https://www.kaggle.com/competitions/%s" % ref
            if not url:
                continue
            deadline = str(item.get("deadline") or "").strip() or None
            mapping[norm_link(url)] = {
                "deadline": deadline,
                "source_schedule_text": deadline,
                "raw_schedule": {
                    "deadline": deadline,
                    "enabledDate": item.get("enabledDate"),
                },
            }
        time.sleep(max(0.0, delay))
    print("Kaggle 线索: %d 条" % len(mapping))
    return mapping


def call_deepseek_schedule(item, api_key, model, base_url, timeout):
    """仅请模型从线索提取日期；禁止臆造。"""
    url = base_url.rstrip("/") + "/chat/completions"
    candidate = {
        "name": item.get("name"),
        "link": item.get("link"),
        "description": item.get("description"),
        "published_at": item.get("published_at"),
        "edition": item.get("edition"),
        "kind": item.get("kind"),
        "brand_id": item.get("brand_id"),
    }
    user = (
        "从下列竞赛信息中提取明确的报名/比赛日期。只有线索里出现明确年月日才能填写。"
        "模糊说法填 null。禁止臆造或用往届规律。\n"
        + json.dumps(candidate, ensure_ascii=False, indent=2)
        + "\n\n只返回 JSON：\n"
        '{"registration_start":"YYYY-MM-DD|null","registration_end":"YYYY-MM-DD|null",'
        '"competition_start":"YYYY-MM-DD|null","competition_end":"YYYY-MM-DD|null",'
        '"schedule_confidence":"high|medium|low","reason":"一句话"}'
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是竞赛日期提取器。只规范化用户给出的明确日期，绝不编造。"
                    "只输出一个 JSON 对象。"
                ),
            },
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "stream": False,
    }
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def apply_schedule_to_item(item, schedule):
    """就地升级；成功返回 True。"""
    link = item.get("link")
    if not can_auto_verify(link, schedule):
        return False
    item["needs_review"] = False
    item["last_checked"] = today_iso()
    for field in SCHEDULE_FIELDS:
        if schedule.get(field):
            item[field] = schedule[field]
        elif field in item:
            # 不应残留
            item.pop(field, None)
    if schedule.get("schedule_source"):
        item["schedule_source"] = schedule["schedule_source"]
    if schedule.get("schedule_confidence"):
        item["schedule_confidence"] = schedule["schedule_confidence"]
    return True


def build_hint_record(item, live_hint):
    record = {
        "name": item.get("name"),
        "link": item.get("link"),
        "description": item.get("description"),
        "published_at": item.get("published_at"),
        "source_list": item.get("brand_id"),
    }
    # 条目上若误留了字段也读
    for field in SCHEDULE_FIELDS:
        if item.get(field):
            record[field] = item.get(field)
    if live_hint:
        record.update({k: v for k, v in live_hint.items() if k != "name"})
    return record


def scrape_page_schedule(url, timeout=25):
    """从赛事页 HTML 轻量提取日期（Devpost 等 SSR 页有效；纯 SPA 常无效）。"""
    if not url:
        return None
    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=timeout, allow_redirects=True
        )
        response.raise_for_status()
        text = response.text[:120000]
    except requests.RequestException:
        return None

    periods = re.findall(r"submission_period_dates\"?\s*:\s*\"([^\"]+)\"", text)
    periods += re.findall(
        r"([A-Za-z]{3,9}\s+\d{1,2}\s*[-–]\s*[A-Za-z]{3,9}\s+\d{1,2},?\s*20\d{2})",
        text,
    )
    start = end = None
    for period in periods:
        start, end = parse_english_range(period)
        if start or end:
            break
    if not (start or end):
        # 优先从含 submit/deadline/registration 的邻近片段取 ISO
        window_hits = re.findall(
            r"(?i)(?:submission|deadline|register|registration|opens?|closes?)[^0-9]{0,40}"
            r"(20\d{2}-\d{2}-\d{2})",
            text,
        )
        isos = window_hits or re.findall(r"20\d{2}-\d{2}-\d{2}", text)
        uniq = sorted(set(isos))
        if len(uniq) >= 2:
            start, end = uniq[0], uniq[-1]
        elif len(uniq) == 1:
            end = uniq[0]
    if not (start or end):
        return None
    return clean_schedule(
        {
            "registration_start": start,
            "registration_end": end,
            "competition_end": end if not start else None,
        },
        "source",
        "high",
    )


def main():
    parser = argparse.ArgumentParser(description="补审 needs_review 旧条目")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="最多处理条数，0=全部")
    parser.add_argument("--skip-model", action="store_true", help="不调用 DeepSeek")
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL))
    parser.add_argument(
        "--base-url", default=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
    )
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--devpost-pages", type=int, default=6)
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not args.skip_model and not api_key:
        print("缺少 DEEPSEEK_API_KEY；将仅做源侧重抓（可用环境变量或 --skip-model）", file=sys.stderr)

    doc = load_json(COMPETITIONS_PATH)
    competitions = doc.get("competitions") or []
    pending = [c for c in competitions if c.get("needs_review")]
    if args.limit and args.limit > 0:
        pending = pending[: args.limit]
    print("待补审: %d 条" % len(pending))

    devpost_map = fetch_devpost_schedule_map(pages=args.devpost_pages)
    kaggle_map = fetch_kaggle_schedule_map()

    upgraded = []
    still_pending = []
    errors = []

    for index, item in enumerate(pending, 1):
        name = item.get("name")
        link = item.get("link")
        key = norm_link(link)
        live = None
        if key in devpost_map:
            live = devpost_map[key]
        elif key in kaggle_map:
            live = kaggle_map[key]

        schedule = schedule_from_source_record(build_hint_record(item, live))
        source_tag = schedule.get("schedule_source")

        # 源 API 没命中时，尝试打开赛事页抓日期（Devpost 等）
        if not has_usable_schedule(schedule) and link:
            page_schedule = scrape_page_schedule(link, timeout=min(25, args.timeout))
            if has_usable_schedule(page_schedule):
                schedule = page_schedule
                source_tag = "source"

        if not has_usable_schedule(schedule) and api_key and not args.skip_model:
            try:
                raw = call_deepseek_schedule(
                    item, api_key, args.model, args.base_url, args.timeout
                )
                conf = str(raw.get("schedule_confidence") or "").strip().lower()
                if conf == "high":
                    schedule = clean_schedule(raw, "model", "high")
                    source_tag = "model"
                time.sleep(max(0.0, args.delay))
            except (requests.RequestException, ValueError, KeyError) as error:
                errors.append({"name": name, "error": str(error)})
                print("  [%d] 模型失败: %s (%s)" % (index, name, error), file=sys.stderr)

        if apply_schedule_to_item(item, schedule):
            upgraded.append(
                {
                    "id": item.get("id"),
                    "name": name,
                    "via": source_tag or schedule.get("schedule_source"),
                }
            )
            print(
                "  [%d/%d] 升级 %s <- %s"
                % (index, len(pending), name, source_tag or schedule.get("schedule_source"))
            )
        else:
            still_pending.append(item.get("id"))
            print("  [%d/%d] 仍待核验 %s" % (index, len(pending), name))

    if not args.dry_run and upgraded:
        dump_json(COMPETITIONS_PATH, doc)
        print("已写入 %s" % COMPETITIONS_PATH)
    elif args.dry_run:
        print("[dry-run] 未写入文件")

    print(
        "完成: 升级 %d / 仍待核验 %d / 模型错误 %d"
        % (len(upgraded), len(still_pending), len(errors))
    )
    for row in upgraded[:30]:
        print("  + %s (%s)" % (row["name"], row["via"]))
    if len(upgraded) > 30:
        print("  ... 另有 %d 条" % (len(upgraded) - 30))
    return 0


if __name__ == "__main__":
    sys.exit(main())
