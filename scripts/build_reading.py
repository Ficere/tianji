#!/usr/bin/env python3
"""将 fortune_calc.py 的确定性计算结果转换为 schema-valid reading.json 骨架。"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from reading_contract import ENGINE_VERSION, SCHEMA_VERSION, validate_reading


MAJOR_STARS = {
    "紫微", "天机", "太阳", "武曲", "天同", "廉贞", "天府",
    "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军",
}
WX_KEYS = {"木": "wood", "火": "fire", "土": "earth", "金": "metal", "水": "water"}
SCENARIOS = {"情侣/伴侣", "亲子", "职场搭档", "团队协作", "管理者与下属", "朋友"}


def _pct_scores(wx: dict[str, float]) -> dict[str, float]:
    total = sum(float(wx.get(cn, 0)) for cn in WX_KEYS) or 1.0
    return {en: round(float(wx.get(cn, 0)) / total * 100, 1) for cn, en in WX_KEYS.items()}


def _strength(person: dict[str, Any]) -> str:
    label = ((person.get("deep") or {}).get("day_master") or {}).get("标签", "中")
    if "极弱" in label:
        return "极弱"
    if "弱" in label:
        return "弱"
    if "旺" in label:
        return "旺"
    if "强" in label:
        return "强"
    return "中"


def _current_ziwei_dayun(person: dict[str, Any]) -> dict[str, str]:
    sequence = (person.get("ziwei") or {}).get("大限序列") or []
    birth_year = int(person.get("solar_date", "2000").split("-")[0])
    nominal_age = datetime.now().year - birth_year + 1
    current = sequence[0] if sequence else {}
    for item in sequence:
        nums = [int(x) for x in re.findall(r"\d+", item.get("年龄范围", ""))]
        if len(nums) >= 2 and nums[0] <= nominal_age <= nums[1]:
            current = item
            break
    stars = "、".join(s for s in current.get("主星", []) if s in MAJOR_STARS) or "空宫"
    return {
        "age_range": current.get("年龄范围", "未计算"),
        "palace": current.get("宫位", "未计算"),
        "star": stars,
        "interpretation": "此处仅呈现确定性排盘结果；具体解读应结合用户问题并标注为民俗参考。",
    }


def _name_analysis(wuge: dict[str, Any] | None) -> dict[str, Any] | None:
    if not wuge:
        return None
    strokes = {x["字"]: x["康熙笔画"] for x in wuge.get("笔画明细", [])}
    grids = wuge.get("五格", {})
    score = float(wuge.get("综合评分", 0))
    if score >= 90:
        rating = "大吉"
    elif score >= 80:
        rating = "吉"
    elif score >= 70:
        rating = "中吉"
    elif score >= 60:
        rating = "中"
    elif score >= 50:
        rating = "小凶"
    else:
        rating = "凶"
    return {
        "strokes_breakdown": strokes,
        "sancai": (wuge.get("三才") or {}).get("配置", "未知"),
        "wuge_scores": {
            "tianGe": (grids.get("天格") or {}).get("数理", 0),
            "renGe": (grids.get("人格") or {}).get("数理", 0),
            "diGe": (grids.get("地格") or {}).get("数理", 0),
            "waiGe": (grids.get("外格") or {}).get("数理", 0),
            "zongGe": (grids.get("总格") or {}).get("数理", 0),
        },
        "overall_rating": rating,
        "interpretation": f"确定性综合评分为 {score:g}；数理含义属于民俗体系，不应用于重大决策。",
    }


def _person_reading(person: dict[str, Any], index: int) -> dict[str, Any]:
    bazi = person["bazi"]
    deep = person.get("deep") or {}
    yongshen = deep.get("yongshen") or {}
    ziwei = person.get("ziwei") or {}
    main = [s for s in ziwei.get("命宫主星", []) if s in MAJOR_STARS]
    patterns = ziwei.get("格局识别", [])
    pattern_text = "、".join(p[0] if isinstance(p, (list, tuple)) else str(p) for p in patterns) or "未识别特定格局"
    sihua = ziwei.get("四化飞星", {})
    sihua_text = "；".join(
        f"{kind}{detail.get('星曜', '')}入{detail.get('所在宫位', '')}"
        for kind, detail in sihua.items()
    ) or "四化信息未计算"
    wx = person.get("wx_canggan") or person.get("wx") or {}
    max_wx = max(wx, key=wx.get) if wx else "未知"
    min_wx = min(wx, key=wx.get) if wx else "未知"
    chenggu = person.get("chenggu") or {}
    warnings = person.get("warnings") or []
    has_city = bool(person.get("birth_city"))

    result = {
        "person_index": index,
        "name": person.get("name", f"成员{index}"),
        "birth_datetime": f"{person.get('solar_date', '')} {person.get('birth_time', '')}",
        "birth_city": person.get("birth_city", ""),
        "gender": {"男": "male", "女": "female"}.get(person.get("gender"), "unknown"),
        "bazi": {
            "pillars": {"year": bazi[0], "month": bazi[1], "day": bazi[2], "hour": bazi[3]},
            "day_master": f"{person.get('day_gan', '')}{({'甲':'木','乙':'木','丙':'火','丁':'火','戊':'土','己':'土','庚':'金','辛':'金','壬':'水','癸':'水'}).get(person.get('day_gan'), '')}",
            "strength": _strength(person),
            "wuxing_distribution": {
                "scores": _pct_scores(wx),
                "strong": [max_wx],
                "weak": [min_wx],
                "absent": person.get("missing_wx", []),
            },
            "ten_gods_summary": "四柱十神依次为：" + "、".join(person.get("shishen", [])) + "。",
            "overall_analysis": "本段由确定性计算骨架生成，完整解读应结合用户问题补充；不得把民俗推演表述为事实。",
            "lucky_elements": yongshen.get("喜神", []),
            "unlucky_elements": yongshen.get("忌神", []),
            "yongshen": yongshen.get("用神") or "",
            "yongshen_basis": yongshen.get("取用理由") or "",
        },
        "bone_weight": {
            "total_liang": round(float(chenggu.get("总重数", 0)) / 10.0, 2),
            "rating": chenggu.get("等级", "未计算"),
            "poem": chenggu.get("歌诀", ""),
            "interpretation": "称骨为传统民俗分类，只展示计算结果，不作为现实决策依据。",
        },
        "ziwei": {
            "life_palace_star": "、".join(main) or "空宫",
            "life_palace_empty": not bool(main),
            "empty_palace_note": "命宫无十四主星时，应借对宫主星作民俗解读。" if not main else "",
            "pattern": pattern_text,
            "current_dayun": _current_ziwei_dayun(person),
            "sihua_summary": sihua_text,
            "overall_analysis": "此处为确定性星曜落宫摘要；叙事层应同时呈现优势、风险和可验证建议。",
        },
        "western_astro": {
            "sun_sign": person.get("zodiac", "未计算"),
            "moon_sign": person.get("moon_sign", "未计算"),
            "trio_interpretation": person.get("astro_combo_reading", "") or "出生信息不足，未生成三星组合。",
        },
        "name_analysis": _name_analysis(person.get("wuge")),
        "personality_sketch": {
            "inner_core": f"排盘事实：日主为 {person.get('day_gan', '未知')}，命宫主星为 {'、'.join(main) or '空宫'}。解读须结合本人反馈验证。",
            "destiny_direction": "当前阶段信息已写入大限字段；不把趋势描述为必然事件。",
            "outer_expression": person.get("astro_combo_reading", "") or "未提供足够信息形成外在表现假设。",
            "reconciliation_theme": "把报告当作自我观察问题，而不是固定人格或命运结论。",
        },
        "confidence_table": {
            "bazi": 4.5,
            "bone_weight": 3.0,
            "ziwei": 4.0,
            "western_astro": 4.0 if has_city else 3.0,
            "name_analysis": 3.0 if person.get("wuge") else 0,
            "personality_sketch": 2.5,
            "confidence_notes": "星级表示输入完整度与计算可复现性，不表示命理观点具有统计预测准确率。"
                                + (f" 当前有 {len(warnings)} 项降级告警。" if warnings else ""),
        },
    }
    if person.get("rising_sign"):
        result["western_astro"]["rising_sign"] = person["rising_sign"]
    if person.get("mbti"):
        result["mbti"] = person["mbti"]
    return result


def _synastry_reading(raw: dict[str, Any], scenario: str) -> dict[str, Any]:
    cs = raw["composite_scores"]
    max_possible = float(raw.get("max_possible", 100)) or 100.0
    core_raw = cs["wuxing_balance"]["score"] + cs["wuxing_complete"]["score"] + cs["riZhu"]["score"]
    core = round(core_raw / 45 * 40, 1)
    will = round(cs["shengxiao"]["score"] + cs["xingzuo"]["score"], 1)
    friction = round(25 * (1 - float(cs["total"]) / max_possible), 1)
    return {
        "core_resonance": {"score": core, "description": "由五行与日主分项按比例投影，便于可视化；不是独立预测指标。"},
        "will_synergy": {"score": will, "description": "由生肖与太阳星座分项合成，仅作民俗参考。"},
        "outer_friction": {"score": max(0, min(25, friction)), "description": "由综合未匹配比例映射，分数越高表示需要更多现实沟通验证。"},
        "composite_scores": cs,
        "overall_comment": f"确定性评分为 {raw.get('score', 0)}/{raw.get('max_possible', 100)}，评级为 {raw.get('rating', '')}。请把分项用于提出沟通问题，不用于替代现实判断。",
        "scenario_advice": [{"scenario": scenario, "advice": "先核对各成员的真实目标、边界和近期行为，再决定哪些民俗假设值得保留。"}],
        "compatibility_summary_line": "先用现实互动验证，再把合盘当作观察关系的辅助视角。",
    }


def build_reading(chart: dict[str, Any], *, title: str | None = None, scenario: str | None = None) -> dict[str, Any]:
    members = chart.get("members") or []
    if not members:
        raise ValueError("chart.json 缺少 members")
    scene = "personal" if len(members) == 1 else "synastry"
    scenario = scenario or ("团队协作" if len(members) > 2 else "朋友")
    if scenario not in SCENARIOS:
        raise ValueError(f"不支持的场景：{scenario}")
    reading = {
        "meta": {
            "scene": scene,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "version": SCHEMA_VERSION,
            "engine_version": ENGINE_VERSION,
            "title": title or ("天机个人命理报告" if scene == "personal" else "天机多人合盘报告"),
            "notes": "计算结果可复现；命理解读属于民俗文化参考，不构成现实决策依据。",
        },
        "persons": [_person_reading(person, i) for i, person in enumerate(members, start=1)],
        "synastry": _synastry_reading(chart["synastry"], scenario) if scene == "synastry" else None,
    }
    return validate_reading(reading)


def main() -> None:
    parser = argparse.ArgumentParser(description="天机 v8.3 reading.json 骨架生成器")
    parser.add_argument("--chart", required=True, help="fortune_calc.py 生成的 chart.json")
    parser.add_argument("--output", default="reading.json")
    parser.add_argument("--title")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS))
    args = parser.parse_args()

    chart = json.loads(Path(args.chart).read_text(encoding="utf-8"))
    reading = build_reading(chart, title=args.title, scenario=args.scenario)
    Path(args.output).write_text(json.dumps(reading, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[天机] reading.json 骨架已生成：{args.output}")


if __name__ == "__main__":
    main()
