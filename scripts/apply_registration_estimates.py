# -*- coding: utf-8 -*-
"""
为南邮固定清单品牌生成「预计」下届报名窗口（P1）。

规则：
- 仅 njupt_fixed 品牌
- 仅当该品牌存在已核验的历史 registration_start/end
- 官方 registration_* 若已覆盖未来/在报窗口，则不写预计
- 写入 registration_*_estimated + schedule_source=estimated
- 不臆造无历史品牌的日期
"""
from __future__ import print_function

import argparse
import json
import os
import sys
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import link_integrity  # noqa: E402

BRANDS_PATH = os.path.join(ROOT, "data", "brands.json")
COMPS_PATH = os.path.join(ROOT, "data", "competitions.json")
# 周更 / 本机默认识「今天」；单测与复现可传 --today YYYY-MM-DD
DEFAULT_TODAY = date.today()


def parse(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def iso(d):
    return d.isoformat() if d else None


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def dump(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def shift_year(d, year):
    if not d:
        return None
    try:
        return date(year, d.month, d.day)
    except ValueError:
        # Feb 29 → Feb 28
        return date(year, d.month, 28)


def latest_reg_template(items):
    """Pick the verified competition with the latest registration anchor."""
    best = None
    best_key = None
    for c in items:
        if c.get("needs_review") is True:
            continue
        if str(c.get("id", "")).startswith("estimate-"):
            continue
        rs = parse(c.get("registration_start"))
        re = parse(c.get("registration_end"))
        if not rs and not re:
            continue
        key = re or rs
        if best is None or key > best_key:
            best = c
            best_key = key
    if not best:
        return None
    return {
        "rs": parse(best.get("registration_start")),
        "re": parse(best.get("registration_end")),
        "source_id": best.get("id"),
        "source_edition": best.get("edition"),
        "name": best.get("name"),
        "kind": best.get("kind"),
        "eligibility": best.get("eligibility") or "高校在校生；细则见官网",
        "category": list(best.get("category") or ["综合"]),
        "link": best.get("link"),
    }


def project_window(template, today):
    """Project last rs/re to a future cycle (keep month/day)."""
    rs = template["rs"]
    re = template["re"]
    if not rs and not re:
        return None

    # Base year from the later of start/end
    base = re or rs
    year = base.year + 1
    # Keep advancing until the window is not entirely in the past
    for _ in range(0, 6):
        nrs = shift_year(rs, year) if rs else None
        nre = shift_year(re, year if not rs else (year if (re and re.year == rs.year) else year + (re.year - rs.year))) if re else None
        # If rs/re spanned years (e.g. Oct 2025 – Mar 2026), preserve delta years
        if rs and re and re.year != rs.year:
            nrs = shift_year(rs, year)
            nre = shift_year(re, year + (re.year - rs.year))
        elif rs and re:
            nrs = shift_year(rs, year)
            nre = shift_year(re, year)
        elif re and not rs:
            nre = shift_year(re, year)
            nrs = None
        else:
            nrs = shift_year(rs, year)
            nre = None

        # 仅有截止日时补默认报名窗口，避免「无开始日」被状态机当成长期报名中
        if nre and not nrs:
            from datetime import timedelta

            nrs = nre - timedelta(days=21)
        if nrs and nre and nrs > nre:
            nrs = nre

        end_anchor = nre or nrs
        if end_anchor and end_anchor >= today:
            # 整段已过则继续推下一年
            if nre and nre < today:
                year += 1
                continue
            if (not nre) and nrs and nrs < today:
                year += 1
                continue
            return nrs, nre, year
        year += 1
    return None


def brand_has_actionable_official(items, today):
    for c in items:
        if c.get("needs_review") is True:
            continue
        if str(c.get("id", "")).startswith("estimate-"):
            continue
        rs = parse(c.get("registration_start"))
        re = parse(c.get("registration_end"))
        if rs and rs > today:
            return True
        if re and re >= today and (not rs or rs <= today):
            return True
    return False


def estimate_home_only(brand):
    """
    预计记录只允许品牌官网根地址，禁止：
    - 拼接 ?estimate= 伪参数
    - 复用往届已失效的深链接（会造成「打不开」的假信息）
    无可靠官网则返回 None，调用方不得写入该预计记录。
    """
    home = (brand.get("official_home") or "").strip()
    if not home:
        return None
    if link_integrity.url_has_fake_markers(home):
        return None
    # 不追加任何虚构 query；展示侧用品牌主页
    return home.rstrip("/")


def assert_estimate_record_honest(record, brand):
    """写入前硬断言：任何违规直接中止，禁止半套交付。"""
    errors = link_integrity.check_competition_link_honesty(
        record, brand, prefix=record.get("id") or "estimate"
    )
    # 双保险：记录本体不得带 link 字段
    if "link" in record and record.get("link"):
        errors.append("%s 内部错误：record 含 link" % record.get("id"))
    if record.get("link_kind") != "brand_home":
        errors.append("%s 内部错误：link_kind 必须为 brand_home" % record.get("id"))
    if errors:
        raise RuntimeError(
            "预计记录链接诚信失败，已中止写入:\n  - " + "\n  - ".join(errors)
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--today",
        default=DEFAULT_TODAY.isoformat(),
        help="Anchor date YYYY-MM-DD (default: local today; weekly-sync uses runner date)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    today = parse(args.today) or DEFAULT_TODAY

    brands_doc = load(BRANDS_PATH)
    comps_doc = load(COMPS_PATH)
    brands = brands_doc["brands"]
    comps = comps_doc["competitions"]
    fixed = [b for b in brands if b.get("njupt_fixed")]
    by_brand = {}
    for c in comps:
        by_brand.setdefault(c.get("brand_id"), []).append(c)

    created = []
    updated = []
    skipped = []

    for brand in fixed:
        bid = brand["brand_id"]
        items = by_brand.get(bid) or []
        if brand_has_actionable_official(items, today):
            skipped.append((bid, "has_official_actionable"))
            continue
        template = latest_reg_template(items)
        if not template:
            skipped.append((bid, "no_verified_reg_history"))
            continue
        projected = project_window(template, today)
        if not projected:
            skipped.append((bid, "project_failed"))
            continue
        nrs, nre, year = projected
        est_id = "estimate-%s-%s" % (bid, year)

        # remove older estimate-* for this brand
        comps = [
            c
            for c in comps
            if not (
                c.get("brand_id") == bid
                and str(c.get("id", "")).startswith("estimate-")
            )
        ]

        # 预计记录禁止写赛事深链：往届 URL / ?estimate= 都会变成假信息。
        # 前端走品牌 official_home，按钮文案「赛事主页」。
        home = estimate_home_only(brand)
        if not home:
            skipped.append((bid, "no_official_home"))
            continue

        note = "据 %s 届报名窗口推算；入口为品牌官网，非本届报名页" % (
            template.get("source_edition") or template.get("source_id")
        )
        record = {
            "id": est_id,
            "brand_id": bid,
            "edition": str(year),
            "track_id": "estimate-main",
            "name": "%s（%s 预计报名）" % (brand.get("name"), year),
            "kind": brand.get("kind") or template.get("kind") or "全国赛事",
            "info_channel": "官方渠道",
            "description": (
                "校认定固定清单。报名日为据往年已核验记录推算的预计时间，"
                "不构成官方通知；不提供本届报名深链（避免失效/伪造链接），"
                "请从赛事品牌官网与校内通知自行核对。"
            ),
            "eligibility": template.get("eligibility"),
            "active": True,
            "needs_review": False,
            "last_checked": iso(today),
            "registration_start_estimated": iso(nrs),
            "registration_end_estimated": iso(nre),
            "schedule_source": "estimated",
            "estimate_note": note,
            "estimate_basis_id": template.get("source_id"),
            # 故意不写 link：避免与品牌首页重复，也禁止伪深链
            "link_kind": "brand_home",
            "tags": ["校认定", "固定清单", "预计"],
            "category": template.get("category") or ["综合"],
        }
        assert_estimate_record_honest(record, brand)
        comps.append(record)
        created.append(est_id)
        by_brand[bid] = [c for c in comps if c.get("brand_id") == bid]

    comps_doc["competitions"] = comps
    # 落盘前整表再扫一遍，防止历史脏数据或半截写入
    brands_by_id = {b.get("brand_id"): b for b in brands}
    honesty_errors = link_integrity.audit_collections(comps, brands_by_id)
    if honesty_errors:
        raise RuntimeError(
            "链接诚信审计失败，已中止写入:\n  - "
            + "\n  - ".join(honesty_errors[:20])
        )
    if not args.dry_run:
        dump(COMPS_PATH, comps_doc)

    print("today", iso(today))
    print("created_or_replaced", len(created))
    for x in created:
        print("  +", x)
    print("skipped", len(skipped))
    for bid, reason in skipped:
        if reason != "no_verified_reg_history":
            print("  -", bid, reason)
    no_hist = sum(1 for _, r in skipped if r == "no_verified_reg_history")
    print("no_history", no_hist)


if __name__ == "__main__":
    main()
