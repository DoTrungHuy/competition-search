# -*- coding: utf-8 -*-
"""赛程日期解析与核验策略（源字段优先，模型只作补充）。

策略（A+B 合并）：
1. 草稿/API 已带可解析日期 → 直接采用（source）
2. 没有可靠源日期 → 才让 DeepSeek 从原文线索提取（model）
3. 仍得不到合法日期 → needs_review=true，不写公开赛程
"""
from __future__ import print_function

import re
from datetime import date, datetime


ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_IN_TEXT = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
# Jul 01 - Jul 31, 2026 | July 1 – August 2, 2026 | 2026/07/01 - 2026/07/31
MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

SCHEDULE_FIELDS = (
    "registration_start",
    "registration_end",
    "competition_start",
    "competition_end",
)


def valid_iso_date(value):
    if not isinstance(value, str) or not ISO_DATE.match(value.strip()):
        return False
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def normalize_iso(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("null", "none", "n/a", ""):
        return None
    # datetime-ish: 2026-07-24T12:00:00Z
    if "T" in text:
        text = text.split("T", 1)[0]
    if valid_iso_date(text):
        return text
    match = ISO_IN_TEXT.search(text)
    if match:
        candidate = "%s-%s-%s" % match.groups()
        return candidate if valid_iso_date(candidate) else None
    return None


def _month_day_year(month_name, day, year):
    month = MONTHS.get(str(month_name or "").strip(".,").lower())
    if not month:
        return None
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return None


def parse_english_range(text):
    """解析 Devpost 常见 'Jul 01 - Jul 31, 2026' / 'July 1 – August 2, 2026'。"""
    if not text:
        return None, None
    raw = re.sub(r"\s+", " ", str(text)).strip()
    # Mon DD - Mon DD, YYYY
    match = re.search(
        r"([A-Za-z]+)\s+(\d{1,2})\s*[-–—to]+\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(20\d{2})",
        raw,
        re.I,
    )
    if match:
        start = _month_day_year(match.group(1), match.group(2), match.group(5))
        end = _month_day_year(match.group(3), match.group(4), match.group(5))
        return start, end
    # Mon DD, YYYY - Mon DD, YYYY
    match = re.search(
        r"([A-Za-z]+)\s+(\d{1,2}),?\s*(20\d{2})\s*[-–—to]+\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(20\d{2})",
        raw,
        re.I,
    )
    if match:
        start = _month_day_year(match.group(1), match.group(2), match.group(3))
        end = _month_day_year(match.group(4), match.group(5), match.group(6))
        return start, end
    # 单点 Mon DD, YYYY
    match = re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s*(20\d{2})", raw, re.I)
    if match:
        day = _month_day_year(match.group(1), match.group(2), match.group(3))
        return None, day
    # ISO range
    isos = ISO_IN_TEXT.findall(raw)
    if len(isos) >= 2:
        a = "%s-%s-%s" % isos[0]
        b = "%s-%s-%s" % isos[1]
        if valid_iso_date(a) and valid_iso_date(b):
            return a, b
    if len(isos) == 1:
        a = "%s-%s-%s" % isos[0]
        if valid_iso_date(a):
            return None, a
    return None, None


def empty_schedule():
    return {
        "registration_start": None,
        "registration_end": None,
        "competition_start": None,
        "competition_end": None,
        "schedule_source": None,
        "schedule_confidence": None,
    }


def clean_schedule(payload, source_label, confidence):
    """只保留合法 ISO 日期；起止顺序不对则丢弃对应对。"""
    result = empty_schedule()
    if not isinstance(payload, dict):
        return result
    for field in SCHEDULE_FIELDS:
        result[field] = normalize_iso(payload.get(field))
    if (
        result["registration_start"]
        and result["registration_end"]
        and result["registration_start"] > result["registration_end"]
    ):
        result["registration_start"] = None
        result["registration_end"] = None
    if (
        result["competition_start"]
        and result["competition_end"]
        and result["competition_start"] > result["competition_end"]
    ):
        result["competition_start"] = None
        result["competition_end"] = None
    if any(result[field] for field in SCHEDULE_FIELDS):
        result["schedule_source"] = source_label
        result["schedule_confidence"] = confidence
    return result


def schedule_from_source_record(record):
    """优先用采集脚本已写入的结构化字段 / 源文本。"""
    if not isinstance(record, dict):
        return empty_schedule()

    structured = {
        field: record.get(field) for field in SCHEDULE_FIELDS if record.get(field)
    }
    if structured:
        cleaned = clean_schedule(structured, "source", "high")
        if any(cleaned[field] for field in SCHEDULE_FIELDS):
            return cleaned

    # 显式文本线索（fetch 写入）
    texts = []
    for key in (
        "source_schedule_text",
        "submission_period_dates",
        "deadline",
        "registration_period_text",
    ):
        if record.get(key):
            texts.append(str(record.get(key)))
    raw = record.get("raw_schedule") or {}
    if isinstance(raw, dict):
        for value in raw.values():
            if value:
                texts.append(str(value))

    # Kaggle 等：明确 deadline 字段
    deadline = normalize_iso(record.get("deadline"))
    if deadline:
        cleaned = clean_schedule(
            {
                "registration_end": deadline,
                "competition_end": deadline,
            },
            "source",
            "high",
        )
        if has_usable_schedule(cleaned):
            return cleaned

    for text in texts:
        start, end = parse_english_range(text)
        if start or end:
            # 区间文本优先当报名/提交窗口；仅单点则同时记截止
            if start and end:
                payload = {
                    "registration_start": start,
                    "registration_end": end,
                }
            else:
                payload = {
                    "registration_end": end or start,
                    "competition_end": end or start,
                }
            cleaned = clean_schedule(payload, "source", "high")
            if has_usable_schedule(cleaned):
                return cleaned

        iso = normalize_iso(text)
        if iso:
            cleaned = clean_schedule(
                {
                    "registration_end": iso,
                    "competition_end": iso,
                },
                "source",
                "high",
            )
            if has_usable_schedule(cleaned):
                return cleaned

    return empty_schedule()


def has_usable_schedule(schedule):
    if not isinstance(schedule, dict):
        return False
    return any(schedule.get(field) for field in SCHEDULE_FIELDS)


def can_auto_verify(record_link, schedule):
    """有深链接 + 至少一项合法赛程 → 可 needs_review=false。"""
    if not record_link:
        return False
    return has_usable_schedule(schedule)


def today_iso():
    return date.today().isoformat()
