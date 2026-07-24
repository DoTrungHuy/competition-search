# -*- coding: utf-8 -*-
"""用 DeepSeek 审核采集草稿，判断是否为真实学生竞赛，并按需补充赛程。

流程定位（自动化管线的第二步）：

    采集脚本 -> draft_*.json -> [本脚本审核] -> reviewed.json -> apply 合并

赛程策略（源优先 + 模型补充）：
1. 草稿/API 已带可解析日期 → 直接采用，不让模型编日期
2. 没有源日期 → 请 DeepSeek 仅从给定线索提取（禁止臆造）
3. 仍无合法日期 → 留给 apply 标 needs_review

依赖环境变量 DEEPSEEK_API_KEY。默认模型 deepseek-chat。
"""
from __future__ import print_function

import argparse
import glob
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

import requests

from schedule_utils import (
    SCHEDULE_FIELDS,
    clean_schedule,
    empty_schedule,
    has_usable_schedule,
    schedule_from_source_record,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_GLOB = os.path.join(ROOT, "scripts", "out", "draft_*.json")
DEFAULT_OUT = os.path.join(ROOT, "scripts", "out", "reviewed.json")
BRANDS_PATH = os.path.join(ROOT, "data", "brands.json")

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
KINDS = ("全国赛事", "大厂赛事", "国际赛事", "校级赛事")

SYSTEM_PROMPT = (
    "你是竞赛数据审核员，负责判断一条采集到的通知是否是面向大学生的"
    "『竞赛报名 / 选拔 / 正在组织参赛』机会。"
    "日期只能从用户提供的线索中提取或规范化，严禁臆造、推算、用往届规律填日期。"
    "严格只输出一个 JSON 对象，不要输出多余文字。"
)


class ReviewError(RuntimeError):
    pass


def valid_url(value):
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def slugify_brand_id(value):
    slug = re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower())
    slug = slug.strip("_")
    return slug or None


def load_brands():
    with open(BRANDS_PATH, "r", encoding="utf-8") as handle:
        brands = json.load(handle).get("brands", [])
    compact = []
    for brand in brands:
        compact.append(
            {
                "brand_id": brand.get("brand_id"),
                "name": brand.get("name"),
                "aliases": brand.get("aliases") or [],
                "kind": brand.get("kind"),
            }
        )
    return compact


def build_messages(record, brands, source_schedule, need_model_schedule):
    """构造发给 DeepSeek 的对话，要求返回结构化审核 JSON。"""
    brand_lines = "\n".join(
        "- %s | %s | 别名: %s | %s"
        % (b["brand_id"], b["name"], "、".join(b["aliases"]), b["kind"])
        for b in brands
        if b["brand_id"]
    )
    candidate = {
        "name": record.get("name"),
        "link": record.get("link"),
        "info_channel": record.get("info_channel"),
        "source_list_name": record.get("source_list_name"),
        "published_at": record.get("published_at"),
        "kind_guess": record.get("kind"),
        "brand_id_guess": record.get("brand_id"),
        "description": record.get("description"),
        "source_schedule_text": record.get("source_schedule_text"),
        "deadline": record.get("deadline"),
        "raw_schedule": record.get("raw_schedule"),
    }
    if has_usable_schedule(source_schedule):
        candidate["already_parsed_schedule"] = {
            field: source_schedule.get(field) for field in SCHEDULE_FIELDS
        }

    schedule_rules = (
        "5. 赛程：源侧已解析出日期（见 already_parsed_schedule）时，"
        "schedule 全部填 null，schedule_confidence 填 null，不要改日期。\n"
        if has_usable_schedule(source_schedule)
        else (
            "5. 赛程：源侧没有可靠日期。仅当线索中出现明确年月日时，"
            "才填写 registration_start/end 或 competition_start/end（格式 YYYY-MM-DD）。"
            "模糊说法（如「7 月下旬」「rolling」「见官网」）一律填 null。"
            "拿不准就全部 null。禁止用往届或常识编日期。\n"
        )
    )

    user_prompt = (
        "已知品牌库（映射到已有 brand_id 时必须从中选择，找不到就填 null）：\n"
        + brand_lines
        + "\n\n合法的赛事类别 kind 只能是：全国赛事 / 大厂赛事 / 国际赛事 / 校级赛事。\n\n"
        "待审核候选（来自采集脚本）：\n"
        + json.dumps(candidate, ensure_ascii=False, indent=2)
        + "\n\n审核规则：\n"
        "1. accept：确为大学生可报名/参加/选拔的具体竞赛或赛道。\n"
        "2. reject：获奖名单、成绩公示、评审结果、基金/资助项目、讲座、培训、"
        "宣讲、报销通知等非报名机会，或与竞赛无关。\n"
        "3. 能对上品牌库已有品牌时，brand_id 填该值、new_brand 置 null。\n"
        "4. 确为真实竞赛但品牌库里没有对应品牌时，brand_id 置 null，并在 new_brand "
        "里提议新品牌：brand_id 用简短小写英文或拼音（如 xjtu_ai），official_home "
        "必须是该赛事官方主页的完整网址（http/https），拿不准官网就把 new_brand 置 null。\n"
        + schedule_rules
        + "\n只返回如下 JSON（字段齐全）：\n"
        '{"verdict":"accept|reject","is_competition":true,'
        '"kind":"全国赛事","brand_id":"lanqiao 或 null",'
        '"new_brand":null 或 {"brand_id":"xxx","name":"赛事全称",'
        '"official_home":"https://...","kind":"全国赛事"},'
        '"confidence":"high|medium|low","reason":"一句话中文理由",'
        '"registration_start":"YYYY-MM-DD 或 null",'
        '"registration_end":"YYYY-MM-DD 或 null",'
        '"competition_start":"YYYY-MM-DD 或 null",'
        '"competition_end":"YYYY-MM-DD 或 null",'
        '"schedule_confidence":"high|medium|low|null"}'
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def call_deepseek(messages, api_key, model, base_url, timeout, retries=2):
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "stream": False,
    }
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=timeout
            )
            if response.status_code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except (requests.RequestException, KeyError, ValueError) as error:
            last_error = error
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
    raise ReviewError("DeepSeek 调用失败: %s" % last_error)


def normalize_new_brand(proposal, existing_ids):
    """校验 DeepSeek 提议的新品牌；不合法返回 None。"""
    if not isinstance(proposal, dict):
        return None
    brand_id = slugify_brand_id(proposal.get("brand_id"))
    name = str(proposal.get("name") or "").strip()
    official_home = str(proposal.get("official_home") or "").strip()
    kind = proposal.get("kind")
    if not brand_id or brand_id in existing_ids:
        return None
    if not name or not valid_url(official_home) or kind not in KINDS:
        return None
    return {
        "brand_id": brand_id,
        "name": name,
        "official_home": official_home,
        "kind": kind,
    }


def normalize_decision(decision, brand_ids, source_schedule):
    verdict = str(decision.get("verdict") or "").strip().lower()
    if verdict not in ("accept", "reject"):
        verdict = "reject"
    kind = decision.get("kind")
    if kind not in KINDS:
        kind = None
    brand_id = decision.get("brand_id")
    if brand_id in ("null", "", None) or brand_id not in brand_ids:
        brand_id = None
    new_brand = None
    if not brand_id:
        new_brand = normalize_new_brand(decision.get("new_brand"), brand_ids)
    confidence = str(decision.get("confidence") or "low").strip().lower()
    if confidence not in ("high", "medium", "low"):
        confidence = "low"

    # 源日期优先；否则仅接受模型 high 置信的合法日期
    if has_usable_schedule(source_schedule):
        schedule = dict(source_schedule)
    else:
        conf = str(decision.get("schedule_confidence") or "").strip().lower()
        if conf not in ("high", "medium", "low"):
            conf = "low"
        model_schedule = clean_schedule(decision, "model", conf)
        # 只有 high 才采用模型日期，medium/low 视为不可靠 → 待核验
        if conf == "high" and has_usable_schedule(model_schedule):
            schedule = model_schedule
        else:
            schedule = empty_schedule()

    result = {
        "verdict": verdict,
        "is_competition": bool(decision.get("is_competition")),
        "kind": kind,
        "brand_id": brand_id,
        "new_brand": new_brand,
        "confidence": confidence,
        "reason": str(decision.get("reason") or "").strip(),
    }
    for field in SCHEDULE_FIELDS:
        result[field] = schedule.get(field)
    result["schedule_source"] = schedule.get("schedule_source")
    result["schedule_confidence"] = schedule.get("schedule_confidence")
    return result


def iter_candidates(draft):
    """从草稿里取出需要审核的 new 和 changed 记录。"""
    review = draft.get("review", {})
    for record in review.get("new", []):
        yield record
    for entry in review.get("changed", []):
        record = dict(entry.get("record") or {})
        record["_changed_fields"] = entry.get("changed_fields")
        yield record


def main():
    parser = argparse.ArgumentParser(description="用 DeepSeek 审核采集草稿")
    parser.add_argument(
        "--in",
        dest="infiles",
        nargs="*",
        default=None,
        help="草稿 JSON 路径（默认扫描 scripts/out/draft_*.json）",
    )
    parser.add_argument("--out", default=DEFAULT_OUT, help="审核结果 JSON 路径")
    parser.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL))
    parser.add_argument("--base-url", default=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout", type=int, default=60, help="单次请求超时秒数")
    parser.add_argument("--delay", type=float, default=0.5, help="请求间隔秒")
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("缺少环境变量 DEEPSEEK_API_KEY", file=sys.stderr)
        return 2

    files = args.infiles if args.infiles else sorted(glob.glob(DEFAULT_GLOB))
    files = [path for path in files if os.path.isfile(path)]

    brands = load_brands()
    brand_ids = {b["brand_id"] for b in brands if b["brand_id"]}

    accepted = []
    rejected = []
    errors = []
    candidates = []
    source_schedule_hits = 0
    model_schedule_hits = 0
    for path in files:
        with open(path, "r", encoding="utf-8") as handle:
            candidates.extend(iter_candidates(json.load(handle)))
    print("草稿文件: %d 个，待审核候选: %d 条" % (len(files), len(candidates)))

    for index, record in enumerate(candidates, 1):
        name = record.get("name")
        source_schedule = schedule_from_source_record(record)
        need_model_schedule = not has_usable_schedule(source_schedule)
        try:
            raw = call_deepseek(
                build_messages(record, brands, source_schedule, need_model_schedule),
                api_key,
                args.model,
                args.base_url,
                args.timeout,
            )
            decision = normalize_decision(raw, brand_ids, source_schedule)
        except ReviewError as error:
            errors.append({"name": name, "link": record.get("link"), "error": str(error)})
            print("  [%d/%d] 失败: %s" % (index, len(candidates), name), file=sys.stderr)
            continue

        if decision.get("schedule_source") == "source":
            source_schedule_hits += 1
        elif decision.get("schedule_source") == "model":
            model_schedule_hits += 1

        bucket = accepted if decision["verdict"] == "accept" else rejected
        bucket.append({"record": record, "decision": decision})
        sched_tag = decision.get("schedule_source") or "none"
        print(
            "  [%d/%d] %s <- %s (%s) schedule=%s"
            % (
                index,
                len(candidates),
                decision["verdict"],
                name,
                decision["confidence"],
                sched_tag,
            )
        )
        time.sleep(max(0.0, args.delay))

    output = {
        "meta": {
            "model": args.model,
            "source_drafts": [os.path.basename(path) for path in files],
            "counts": {
                "accepted": len(accepted),
                "rejected": len(rejected),
                "errors": len(errors),
                "schedule_from_source": source_schedule_hits,
                "schedule_from_model": model_schedule_hits,
            },
            "note": (
                "审核结论；赛程源优先、模型仅 high 置信补充；"
                "apply 时有合法赛程+深链接可自动 needs_review=false。"
            ),
        },
        "accepted": accepted,
        "rejected": rejected,
        "errors": errors,
    }

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(
        "完成: 通过 %d / 拒绝 %d / 失败 %d | 源日期 %d / 模型日期 %d"
        % (
            len(accepted),
            len(rejected),
            len(errors),
            source_schedule_hits,
            model_schedule_hits,
        )
    )
    print("结果: %s" % args.out)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
