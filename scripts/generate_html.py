#!/usr/bin/env python3
"""
generate_html.py — 天机 v8.0 HTML 报告渲染器

用法：
    python generate_html.py --reading reading.json [--chart chart.json] [--output tianji_report.html]
"""

import json
import math
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# ════════════════════════════════════════════════════════
# 常量：五行映射
# ════════════════════════════════════════════════════════

WUXING_CN = {"wood": "木", "fire": "火", "earth": "土", "metal": "金", "water": "水"}
WUXING_COLOR = {
    "wood":  "#4a7c59",
    "fire":  "#b5451b",
    "earth": "#c9973a",
    "metal": "#7a6a55",
    "water": "#2c5075",
}
WUXING_ORDER = ["wood", "fire", "earth", "metal", "water"]

# ════════════════════════════════════════════════════════
# 模块 1：数据加载与合并
# ════════════════════════════════════════════════════════

def load_reading(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"reading.json 不存在：{path}")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("meta", {}).get("version") != "8.0":
        raise ValueError("reading.json 版本不符，需为 8.0")
    if not data.get("persons"):
        raise ValueError("reading.json 缺少 persons 字段")
    return data


def load_chart(path: Optional[str]) -> Optional[dict]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def merge_data(reading: dict, chart: Optional[dict]) -> dict:
    """chart.json 数值字段覆盖 reading.json，解读文字保留 reading.json"""
    if not chart:
        return reading
    for i, person in enumerate(reading.get("persons", [])):
        cp = chart.get("persons", [{}] * (i + 1))
        if i >= len(cp):
            continue
        c = cp[i]
        # 五行 scores 覆盖
        if "wuxing" in c and "scores" in c["wuxing"]:
            person.setdefault("bazi", {}).setdefault("wuxing_distribution", {})["scores"] = c["wuxing"]["scores"]
        # 四柱覆盖
        if "pillars" in c:
            person.setdefault("bazi", {})["pillars"] = c["pillars"]
        # 称骨覆盖
        if "bone" in c:
            if "total" in c["bone"]:
                person.setdefault("bone_weight", {})["total_liang"] = c["bone"]["total"]
            if "breakdown" in c["bone"]:
                person.setdefault("bone_weight", {})["breakdown"] = c["bone"]["breakdown"]
        # 星座覆盖
        if "western" in c:
            wa = person.setdefault("western_astro", {})
            for k in ["sun_sign", "moon_sign", "rising_sign"]:
                ck = k.replace("_sign", "")
                if ck in c["western"]:
                    wa[k] = c["western"][ck]
    return reading


# ════════════════════════════════════════════════════════
# 模块 2：可视化组件（条形图 + 星级 + 进度条）
# ════════════════════════════════════════════════════════

def render_wuxing_bars(scores: dict, absent: list = None, lucky: list = None, unlucky: list = None) -> str:
    """五行水平条形图，含旺/弱/缺标签"""
    absent = absent or []
    lucky = lucky or []
    unlucky = unlucky or []
    total = sum(scores.values()) or 1
    rows = []
    for key in WUXING_ORDER:
        cn = WUXING_CN[key]
        color = WUXING_COLOR[key]
        val = scores.get(key, 0)
        pct = val / total * 100
        tags = []
        if cn in absent:
            tags.append('<span class="tag tag-absent">缺</span>')
        if cn in lucky:
            tags.append('<span class="tag tag-lucky">喜</span>')
        if cn in unlucky:
            tags.append('<span class="tag tag-unlucky">忌</span>')
        tag_html = "".join(tags)
        rows.append(f"""
        <div class="wx-bar-row">
          <div class="wx-bar-label">{cn}{tag_html}</div>
          <div class="wx-bar-track">
            <div class="wx-bar-fill" style="--wx-color:{color}; --wx-pct:{pct:.1f}%"></div>
          </div>
          <div class="wx-bar-val">{pct:.0f}%</div>
        </div>""")
    return f'<div class="wuxing-bars">{"".join(rows)}</div>'


def render_star_rating(score: float, max_score: float = 5.0) -> str:
    """SVG 星级，支持半星"""
    stars = []
    full = int(score)
    half = 1 if (score - full) >= 0.4 else 0
    empty = int(max_score) - full - half
    for _ in range(full):
        stars.append('<svg class="star star-full" viewBox="0 0 20 20"><polygon points="10,1 12.9,7 19.5,7.6 14.5,12 16.2,18.5 10,15 3.8,18.5 5.5,12 0.5,7.6 7.1,7"/></svg>')
    if half:
        stars.append('<svg class="star star-half" viewBox="0 0 20 20"><defs><linearGradient id="hg"><stop offset="50%" stop-color="var(--color-gold)"/><stop offset="50%" stop-color="var(--color-border)"/></linearGradient></defs><polygon points="10,1 12.9,7 19.5,7.6 14.5,12 16.2,18.5 10,15 3.8,18.5 5.5,12 0.5,7.6 7.1,7" fill="url(#hg)"/></svg>')
    for _ in range(empty):
        stars.append('<svg class="star star-empty" viewBox="0 0 20 20"><polygon points="10,1 12.9,7 19.5,7.6 14.5,12 16.2,18.5 10,15 3.8,18.5 5.5,12 0.5,7.6 7.1,7"/></svg>')
    return f'<span class="star-rating" aria-label="{score}星满分{int(max_score)}星">{"".join(stars)}</span>'


def render_score_bar(label: str, score: float, max_score: float, color: str = "var(--color-gold)") -> str:
    pct = score / max_score * 100 if max_score else 0
    return f"""
    <div class="score-bar-row">
      <span class="score-bar-label">{label}</span>
      <div class="score-bar-track">
        <div class="score-bar-fill" style="--bar-color:{color}; --bar-pct:{pct:.1f}%"
             data-score="{score}" data-max="{max_score}"></div>
      </div>
      <span class="score-bar-value">{score:.0f}/{max_score:.0f}</span>
    </div>"""


def render_synastry_gauges(core: float, will: float, friction: float) -> str:
    """三个半圆弧仪表盘 SVG"""
    def arc_svg(value, max_val, color, label, sublabel, invert=False):
        pct = value / max_val if max_val else 0
        if invert:
            display_pct = 1 - pct
            arc_pct = pct
        else:
            display_pct = pct
            arc_pct = pct
        # 半圆弧参数
        r = 54
        cx, cy = 70, 70
        circumference = math.pi * r
        filled = arc_pct * circumference
        gap = circumference - filled
        score_display = f"{value:.0f}/{max_val:.0f}"
        pct_text = f"{display_pct*100:.0f}%"
        return f"""
        <div class="gauge-item">
          <svg viewBox="0 0 140 80" class="gauge-svg">
            <path d="M 16,70 A {r},{r} 0 0 1 124,70"
                  fill="none" stroke="var(--color-border)" stroke-width="10" stroke-linecap="round"/>
            <path d="M 16,70 A {r},{r} 0 0 1 124,70"
                  fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round"
                  stroke-dasharray="{filled:.2f} {gap:.2f}"
                  class="gauge-arc"/>
            <text x="70" y="65" text-anchor="middle" class="gauge-score">{score_display}</text>
          </svg>
          <div class="gauge-label">{label}</div>
          <div class="gauge-sublabel">{sublabel}</div>
        </div>"""

    core_svg     = arc_svg(core,     40, "var(--color-purple)",  "内核共鸣度", f"满分40")
    will_svg     = arc_svg(will,     35, "var(--color-gold)",    "意志协同度", f"满分35")
    friction_svg = arc_svg(friction, 25, "var(--color-muted)",   "外在摩擦点", f"满分25，越高摩擦越大", invert=True)
    return f'<div class="gauges-container">{core_svg}{will_svg}{friction_svg}</div>'


# ════════════════════════════════════════════════════════
# 模块 3：Section 渲染
# ════════════════════════════════════════════════════════

def render_hero(person: dict, is_synastry: bool = False) -> str:
    name = person.get("name", "命主")
    birth = person.get("birth_datetime", "")
    gender_map = {"male": "男", "female": "女", "unknown": ""}
    gender = gender_map.get(person.get("gender", ""), "")
    mbti = person.get("mbti", "")
    bazi = person.get("bazi", {})
    day_master = bazi.get("day_master", "")
    strength = bazi.get("strength", "")
    sketch = person.get("personality_sketch", {})
    reconciliation = sketch.get("reconciliation_theme", "")

    tags = []
    if day_master:
        tags.append(f'<span class="hero-tag">{day_master} · {strength}</span>')
    if mbti:
        tags.append(f'<span class="hero-tag">{mbti}</span>')
    if gender:
        tags.append(f'<span class="hero-tag">{gender}</span>')
    tags_html = "".join(tags)

    reconciliation_html = ""
    if reconciliation and not is_synastry:
        reconciliation_html = f'<p class="hero-quote">「{reconciliation}」</p>'

    return f"""
    <header class="hero-section">
      <div class="hero-inner">
        <h1 class="hero-name">{name}</h1>
        <p class="hero-birth">{birth}</p>
        <div class="hero-tags">{tags_html}</div>
        {reconciliation_html}
      </div>
    </header>"""


def render_bazi_section(person: dict) -> str:
    bazi = person.get("bazi", {})
    pillars = bazi.get("pillars", {})
    dist = bazi.get("wuxing_distribution", {})
    scores = dist.get("scores", {})
    absent = dist.get("absent", [])
    lucky = bazi.get("lucky_elements", [])
    unlucky = bazi.get("unlucky_elements", [])

    pillar_html = ""
    for key, label in [("year","年柱"), ("month","月柱"), ("day","日柱"), ("hour","时柱")]:
        val = pillars.get(key, "—")
        extra = ' class="pillar-day"' if key == "day" else ""
        pillar_html += f'<div class="pillar"{extra}><div class="pillar-label">{label}</div><div class="pillar-ganzhi">{val}</div></div>'

    bars = render_wuxing_bars(scores, absent=absent, lucky=lucky, unlucky=unlucky)
    analysis = bazi.get("overall_analysis", "")
    ten_gods = bazi.get("ten_gods_summary", "")

    return f"""
    <section class="report-section" id="bazi">
      <h2 class="section-title">八字四柱</h2>
      <div class="pillars-row">{pillar_html}</div>
      <div class="bazi-body">
        <div class="bazi-chart">{bars}</div>
        <div class="bazi-analysis">
          <p class="analysis-sub">{ten_gods}</p>
          <p class="analysis-text">{analysis}</p>
        </div>
      </div>
    </section>"""


def render_bone_section(person: dict) -> str:
    bw = person.get("bone_weight", {})
    total = bw.get("total_liang", 0)
    rating = bw.get("rating", "")
    poem = bw.get("poem", "")
    interp = bw.get("interpretation", "")
    breakdown = bw.get("breakdown", {})

    breakdown_html = ""
    if breakdown:
        def _fmt_bone(v):
            if isinstance(v, (int, float)):
                return f'{v:.2f}两'
            return str(v)  # 已是字符串（如 "1两5钱"）直接展示
        parts = [f'{["年","月","日","时"][i]}柱 {_fmt_bone(v)}' for i, (k, v) in enumerate(breakdown.items()) if k in ["year","month","day","hour"]]
        breakdown_html = f'<p class="bone-breakdown">{" ＋ ".join(parts)}</p>'

    poem_lines = "".join(f"<span>{line}</span>" for line in poem.split("。") if line.strip())

    return f"""
    <section class="report-section" id="bone">
      <h2 class="section-title">称骨算命</h2>
      <div class="bone-header">
        <div class="bone-total"><span class="bone-num">{total:.2f}</span><span class="bone-unit">两</span></div>
        <div class="bone-meta">
          <span class="bone-rating">{rating}</span>
          {breakdown_html}
        </div>
      </div>
      <blockquote class="bone-poem">{poem_lines}</blockquote>
      <p class="bone-interp">{interp}</p>
    </section>"""


def render_ziwei_section(person: dict) -> str:
    zw = person.get("ziwei", {})
    star = zw.get("life_palace_star", "")
    pattern = zw.get("pattern", "")
    empty = zw.get("life_palace_empty", False)
    empty_note = zw.get("empty_palace_note", "")
    dayun = zw.get("current_dayun", {})
    sihua = zw.get("sihua_summary", "")
    analysis = zw.get("overall_analysis", "")

    empty_html = ""
    if empty and empty_note:
        empty_html = f'<div class="empty-palace-note">⚠️ 空宫：{empty_note}</div>'

    dayun_html = ""
    if dayun:
        age = dayun.get("age_range", "")
        palace = dayun.get("palace", "")
        dstar = dayun.get("star", "")
        dinterp = dayun.get("interpretation", "")
        dayun_html = f"""
        <div class="dayun-card">
          <div class="dayun-header">
            <span class="dayun-badge">当前大限</span>
            <span class="dayun-age">{age}</span>
            <span class="dayun-palace">{palace} · {dstar}</span>
          </div>
          <p class="dayun-interp">{dinterp}</p>
        </div>"""

    return f"""
    <section class="report-section" id="ziwei">
      <h2 class="section-title">紫微斗数</h2>
      <div class="ziwei-header">
        <div class="ziwei-star-block">
          <span class="ziwei-star-label">命宫主星</span>
          <span class="ziwei-star-name">{star}</span>
        </div>
        <div class="ziwei-pattern">{pattern}</div>
      </div>
      {empty_html}
      {dayun_html}
      <div class="ziwei-analysis">
        <p class="analysis-sub">四化速览：{sihua}</p>
        <p class="analysis-text">{analysis}</p>
      </div>
    </section>"""


def render_western_section(person: dict) -> str:
    wa = person.get("western_astro", {})
    sun = wa.get("sun_sign", "")
    moon = wa.get("moon_sign", "")
    rising = wa.get("rising_sign", "")
    trio = wa.get("trio_interpretation", "")
    aspects = wa.get("key_aspects", "")

    signs = [("☉", "太阳", sun), ("☽", "月亮", moon)]
    if rising:
        signs.append(("↑", "上升", rising))

    badges = "".join(f'<div class="sign-badge"><span class="sign-icon">{icon}</span><span class="sign-name-label">{label}</span><span class="sign-name">{name}</span></div>'
                     for icon, label, name in signs if name)

    aspects_html = f'<p class="aspects-note">{aspects}</p>' if aspects else ""

    return f"""
    <section class="report-section" id="western">
      <h2 class="section-title">西洋星座</h2>
      <div class="signs-row">{badges}</div>
      <p class="analysis-text">{trio}</p>
      {aspects_html}
    </section>"""


def render_name_section(person: dict) -> str:
    na = person.get("name_analysis")
    if not na:
        return ""
    strokes = na.get("strokes_breakdown", {})
    sancai = na.get("sancai", "")
    wuge = na.get("wuge_scores", {})
    rating = na.get("overall_rating", "")
    interp = na.get("interpretation", "")

    stroke_html = " · ".join(f"{char} {n}画" for char, n in strokes.items())

    rating_class = {"大吉": "rating-daji", "吉": "rating-ji", "中吉": "rating-zhongji",
                    "中": "rating-zhong", "小凶": "rating-xiong", "凶": "rating-xiong"}.get(rating, "")

    RATING_COLOR = {"大吉": "#c9973a", "吉": "#4a7c59", "半吉": "#7a6a55", "凶": "#b5451b", "小凶": "#b5451b"}
    wuge_html = ""
    for key, label in [("tianGe","天格"), ("renGe","人格"), ("diGe","地格"), ("waiGe","外格"), ("zongGe","总格")]:
        raw = wuge.get(key, {})
        if isinstance(raw, dict):
            num   = raw.get("value", "—")
            name  = raw.get("name", "")
            gr    = raw.get("rating", "")
            elem  = raw.get("element", "")
        else:
            # 兼容纯数字格式
            num, name, gr, elem = raw, "", "", ""
        gr_color = RATING_COLOR.get(gr, "#7a6a55")
        wuge_html += (
            f'<div class="wuge-item">'
            f'<span class="wuge-label">{label}</span>'
            f'<span class="wuge-num">{num}</span>'
            f'<span class="wuge-name">{name}</span>'
            f'<span class="wuge-elem">{elem}</span>'
            f'<span class="wuge-rating" style="color:{gr_color}">{gr}</span>'
            f'</div>'
        )

    # 三才详情
    sancai_obj = na.get("sancai", {})
    if isinstance(sancai_obj, dict):
        sancai_cfg    = sancai_obj.get("config", "")
        sancai_rating = sancai_obj.get("rating", "")
        sancai_detail = sancai_obj.get("detail", "")
    else:
        sancai_cfg    = str(sancai_obj)
        sancai_rating = ""
        sancai_detail = ""
    sancai_rating_color = RATING_COLOR.get(sancai_rating, "#7a6a55")
    sancai_html = (
        f'三才：<strong>{sancai_cfg}</strong>'
        + (f' <span style="color:{sancai_rating_color}">({sancai_rating})</span>' if sancai_rating else "")
        + (f'<br><small style="color:var(--color-ink-muted)">{sancai_detail}</small>' if sancai_detail else "")
    )

    # 综合评分进度条
    overall_score = na.get("overall_score", na.get("overall_rating", ""))
    score_bar = ""
    if isinstance(overall_score, (int, float)):
        score_bar = f"""
        <div class="name-score-row">
          <span class="name-score-label">综合评分</span>
          <div class="name-score-bar-wrap">
            <div class="name-score-bar" style="width:{min(overall_score,100):.0f}%"></div>
          </div>
          <span class="name-score-num">{overall_score:.1f}</span>
          <span class="name-score-rating {rating_class}">{rating}</span>
        </div>"""
    else:
        score_bar = f'<p><span class="name-rating {rating_class}">{rating}</span></p>'

    return f"""
    <section class="report-section" id="name">
      <h2 class="section-title">三才五格姓名</h2>
      <div class="name-header">
        <span class="name-strokes">{stroke_html}</span>
      </div>
      {score_bar}
      <div class="wuge-row">{wuge_html}</div>
      <div class="sancai-block">{sancai_html}</div>
      <p class="analysis-text">{interp}</p>
    </section>"""


def render_sixdim_section(person: dict) -> str:
    """渲染六维度评分区块：事业/财运/婚姻/健康/子女/精神"""
    dims = person.get("six_dimensions")
    if not dims:
        return ""

    DIM_LABELS = [
        ("career",   "事业"),
        ("wealth",   "财运"),
        ("marriage", "婚姻"),
        ("health",   "健康"),
        ("children", "子女"),
        ("spirit",   "精神"),
    ]
    # 限分100，条形颜色按分段
    def bar_color(score, total=100):
        pct = score / total
        if pct >= 0.8:  return "#c9973a"
        if pct >= 0.6:  return "#4a7c59"
        if pct >= 0.4:  return "#7a6a55"
        return "#b5451b"

    cards_html = ""
    for key, cn_label in DIM_LABELS:
        d = dims.get(key)
        if not d:
            continue
        score   = d.get("score", 0)
        total   = d.get("total", 100)
        label   = d.get("label", "")
        comment = d.get("comment", "")
        pct     = round(min(score / total, 1) * 100)
        color   = bar_color(score, total)
        cards_html += f"""
        <div class="sixdim-card">
          <div class="sixdim-title">{cn_label}</div>
          <div class="sixdim-score-row">
            <span class="sixdim-score-num">{score}</span>
            <span class="sixdim-score-max">/{total}</span>
            <div class="sixdim-bar-wrap">
              <div class="sixdim-bar" style="width:{pct}%;background:{color}"></div>
            </div>
          </div>
          <div class="sixdim-label" style="color:{color}">{label}</div>
          <div class="sixdim-comment">{comment}</div>
        </div>"""

    return f"""
    <section class="report-section" id="sixdim">
      <h2 class="section-title">六维度评分</h2>
      <div class="sixdim-grid">{cards_html}</div>
    </section>"""


def render_sketch_section(person: dict) -> str:
    sk = person.get("personality_sketch", {})
    inner = sk.get("inner_core", "")
    destiny = sk.get("destiny_direction", "")
    outer = sk.get("outer_expression", "")
    reconciliation = sk.get("reconciliation_theme", "")
    mbti_note = sk.get("mbti_integration", "")

    mbti_html = f'<div class="mbti-note"><span class="mbti-label">MBTI 补充</span><p>{mbti_note}</p></div>' if mbti_note else ""

    return f"""
    <section class="report-section" id="sketch">
      <h2 class="section-title">人格速写</h2>
      <div class="sketch-cards">
        <div class="sketch-card">
          <div class="sketch-card-title">内在内核</div>
          <p>{inner}</p>
        </div>
        <div class="sketch-card">
          <div class="sketch-card-title">命运方向</div>
          <p>{destiny}</p>
        </div>
        <div class="sketch-card">
          <div class="sketch-card-title">外在表现</div>
          <p>{outer}</p>
        </div>
      </div>
      <div class="reconciliation-box">
        <span class="reconciliation-label">和解命题</span>
        <p class="reconciliation-text">「{reconciliation}」</p>
      </div>
      {mbti_html}
    </section>"""


def render_confidence_section(person: dict) -> str:
    ct = person.get("confidence_table", {})
    notes = ct.get("confidence_notes", "")

    rows = [
        ("bazi",               "八字四柱"),
        ("ziwei",              "紫微斗数"),
        ("western_astro",      "西洋星座"),
        ("bone_weight",        "称骨算命"),
        ("name_analysis",      "三才五格"),
        ("personality_sketch", "人格速写"),
    ]
    rows_html = ""
    for key, label in rows:
        val = ct.get(key)
        if val is None:
            continue
        rows_html += f"""
        <tr>
          <td class="conf-label">{label}</td>
          <td class="conf-stars">{render_star_rating(val)}</td>
          <td class="conf-val">{val:.1f}</td>
        </tr>"""

    notes_html = f'<p class="conf-notes">{notes}</p>' if notes else ""

    return f"""
    <section class="report-section" id="confidence">
      <h2 class="section-title">置信度评级</h2>
      <table class="conf-table">
        <thead><tr><th>维度</th><th>置信度</th><th>评分</th></tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
      {notes_html}
    </section>"""


def render_person_full(person: dict) -> str:
    """渲染单人完整命盘所有 section"""
    return "".join([
        render_hero(person),
        render_bazi_section(person),
        render_bone_section(person),
        render_ziwei_section(person),
        render_western_section(person),
        render_name_section(person),
        render_sixdim_section(person),
        render_sketch_section(person),
        render_confidence_section(person),
    ])


def render_person_summary(person: dict) -> str:
    """合盘双列中的单人摘要卡片"""
    name = person.get("name", f"命主{person.get('person_index','')}")
    bazi = person.get("bazi", {})
    day_master = bazi.get("day_master", "")
    strength = bazi.get("strength", "")
    dist = bazi.get("wuxing_distribution", {})
    scores = dist.get("scores", {})
    absent = dist.get("absent", [])
    lucky = bazi.get("lucky_elements", [])
    unlucky = bazi.get("unlucky_elements", [])

    zw = person.get("ziwei", {})
    star = zw.get("life_palace_star", "")
    dayun = zw.get("current_dayun", {})
    dayun_html = ""
    if dayun:
        dayun_html = f'<p class="sum-dayun">大限：{dayun.get("age_range","")} · {dayun.get("palace","")} {dayun.get("star","")}</p>'

    wa = person.get("western_astro", {})
    signs = []
    if wa.get("sun_sign"): signs.append(f'☉{wa["sun_sign"]}')
    if wa.get("moon_sign"): signs.append(f'☽{wa["moon_sign"]}')
    if wa.get("rising_sign"): signs.append(f'↑{wa["rising_sign"]}')
    signs_html = " &nbsp; ".join(signs)

    sk = person.get("personality_sketch", {})
    inner = sk.get("inner_core", "")
    inner_short = inner[:60] + "…" if len(inner) > 60 else inner

    bars = render_wuxing_bars(scores, absent=absent, lucky=lucky, unlucky=unlucky)
    idx = person.get("person_index", 1)

    return f"""
    <div class="summary-card">
      <h3 class="sum-name">{name}</h3>
      <div class="sum-meta">{day_master} · {strength}</div>
      {bars}
      <div class="sum-ziwei">命宫：{star}</div>
      {dayun_html}
      <div class="sum-signs">{signs_html}</div>
      <p class="sum-inner">{inner_short}</p>
      <details class="full-detail">
        <summary>展开完整命盘 ▾</summary>
        <div class="full-detail-inner" data-person-idx="{idx}"><!-- 完整命盘见页面底部 --></div>
      </details>
    </div>"""


def render_synastry_scores(synastry: dict) -> str:
    cs = synastry.get("composite_scores", {})
    total = cs.get("total", 0)
    items = [
        ("wuxing_balance",  "五行平衡",  20, "var(--color-gold)"),
        ("wuxing_complete", "五行俱全",   5, "var(--color-gold-light)"),
        ("shengxiao",       "生肖关系",  20, "#8b5e3c"),
        ("xingzuo",         "星座相位",  15, "var(--color-purple)"),
        ("riZhu",           "日主关系",  20, "#3d6b54"),
        ("chenggu",         "称骨对比",  15, "#5a4a8a"),
        ("xingming",        "姓名合盘",   5, "#7a6a55"),
    ]
    bars_html = ""
    for key, label, max_s, color in items:
        item = cs.get(key, {})
        score = item.get("score", 0)
        comment = item.get("comment", "")
        bar = render_score_bar(f"{label}（/{max_s}）", score, max_s, color)
        bars_html += f'<div class="score-item" title="{comment}">{bar}</div>'

    # 总分星级
    total_pct = total / 100
    star_level = min(5.0, total_pct * 5)
    star_label = "★★★★★" if total >= 90 else "★★★★☆" if total >= 75 else "★★★☆☆" if total >= 60 else "★★☆☆☆" if total >= 45 else "★☆☆☆☆"

    return f"""
    <section class="report-section" id="scores">
      <h2 class="section-title">综合评分</h2>
      <div class="total-score-row">
        <span class="total-label">综合总分</span>
        <span class="total-num">{total:.0f}</span>
        <span class="total-denom">/100</span>
        <span class="total-stars">{star_label}</span>
      </div>
      <div class="score-bars">{bars_html}</div>
    </section>"""


def render_scenario_tabs(synastry: dict) -> str:
    advices = synastry.get("scenario_advice", [])
    if not advices:
        return ""
    tabs_html = ""
    panels_html = ""
    for i, item in enumerate(advices):
        sc = item.get("scenario", "")
        adv = item.get("advice", "")
        active = ' class="scenario-tab active"' if i == 0 else ' class="scenario-tab"'
        hidden = "" if i == 0 else " hidden"
        tabs_html += f'<button{active} data-target="scenario-{i}">{sc}</button>'
        panels_html += f'<div class="scenario-content" id="scenario-{i}"{hidden}><p>{adv}</p></div>'

    return f"""
    <section class="report-section" id="scenarios">
      <h2 class="section-title">场景化建议</h2>
      <div class="scenario-tabs">{tabs_html}</div>
      <div class="scenario-panels">{panels_html}</div>
    </section>"""


# ════════════════════════════════════════════════════════
# 模块 4：布局组装
# ════════════════════════════════════════════════════════

def build_personal_page(ctx: dict) -> str:
    person = ctx["persons"][0]
    body = render_person_full(person)
    return body


def build_synastry_page(ctx: dict) -> str:
    persons = ctx["persons"]
    synastry = ctx.get("synastry") or {}
    meta = ctx.get("meta", {})

    p1_name = persons[0].get("name", "命主一") if persons else "命主一"
    p2_name = persons[1].get("name", "命主二") if len(persons) > 1 else "命主二"
    summary_line = synastry.get("compatibility_summary_line", "")
    title = meta.get("title", f"{p1_name} × {p2_name} 合盘")

    # 合盘 hero
    hero_html = f"""
    <header class="hero-section synastry-hero">
      <div class="hero-inner">
        <h1 class="hero-name synastry-title">{p1_name} <span class="synastry-x">×</span> {p2_name}</h1>
        {"" if not summary_line else f'<p class="hero-quote synastry-quote">「{summary_line}」</p>'}
      </div>
    </header>"""

    # 三维仪表
    core_score = synastry.get("core_resonance", {}).get("score", 0)
    will_score = synastry.get("will_synergy", {}).get("score", 0)
    friction_score = synastry.get("outer_friction", {}).get("score", 0)

    core_desc = synastry.get("core_resonance", {}).get("description", "")
    will_desc = synastry.get("will_synergy", {}).get("description", "")
    friction_desc = synastry.get("outer_friction", {}).get("description", "")

    gauge_html = f"""
    <section class="report-section" id="dimensions">
      <h2 class="section-title">三维评分</h2>
      {render_synastry_gauges(core_score, will_score, friction_score)}
      <div class="dim-descriptions">
        <div class="dim-desc"><h4>内核共鸣度 {core_score:.0f}/40</h4><p>{core_desc}</p></div>
        <div class="dim-desc"><h4>意志协同度 {will_score:.0f}/35</h4><p>{will_desc}</p></div>
        <div class="dim-desc"><h4>外在摩擦点 {friction_score:.0f}/25</h4><p>{friction_desc}</p></div>
      </div>
    </section>"""

    # 双列对比
    sum1 = render_person_summary(persons[0]) if persons else ""
    sum2 = render_person_summary(persons[1]) if len(persons) > 1 else ""
    comparison_html = f"""
    <section class="report-section" id="comparison">
      <h2 class="section-title">命盘对比</h2>
      <div class="comparison-grid">{sum1}{sum2}</div>
    </section>"""

    # 综合评分 + 总评 + 场景建议
    scores_html = render_synastry_scores(synastry)
    overall = synastry.get("overall_comment", "")
    overall_html = f"""
    <section class="report-section" id="overall">
      <h2 class="section-title">合盘总评</h2>
      <div class="overall-card"><p>{overall}</p></div>
    </section>""" if overall else ""
    scenarios_html = render_scenario_tabs(synastry)

    # 底部折叠完整命盘
    full_html = ""
    for p in persons:
        pname = p.get("name", f"命主{p.get('person_index','')}")
        full_html += f"""
        <details class="full-person-details" id="full-person-{p.get('person_index',1)}">
          <summary class="full-person-summary">▶ {pname} 完整命盘</summary>
          <div class="full-person-inner">{render_person_full(p)}</div>
        </details>"""

    full_section = f"""
    <section class="report-section" id="full-charts">
      <h2 class="section-title">完整个人命盘</h2>
      {full_html}
    </section>""" if full_html else ""

    return "".join([
        hero_html,
        gauge_html,
        comparison_html,
        scores_html,
        overall_html,
        scenarios_html,
        full_section,
    ])


# ════════════════════════════════════════════════════════
# 模块 5：CSS + JS 内联资源
# ════════════════════════════════════════════════════════

_CSS = """
:root {
  --color-bg-page:       #faf7f2;
  --color-bg-card:       #fff9f0;
  --color-bg-dark:       #1a1410;
  --color-gold:          #c9973a;
  --color-gold-light:    #e8c47a;
  --color-ink:           #2d2318;
  --color-ink-secondary: #6b5a47;
  --color-ink-muted:     #a89880;
  --color-border:        #e4d5bc;
  --color-accent-red:    #8b2020;
  --color-accent-jade:   #3d6b54;
  --color-purple:        #7850a0;
  --color-muted:         #a89880;
  --font-serif: "Noto Serif SC", "Source Han Serif SC", "STSong", "SimSun", serif;
  --font-mono:  "Courier New", monospace;
  --radius:     4px;
  --shadow:     0 2px 12px rgba(139,99,40,.10);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--color-bg-page);
  color: var(--color-ink);
  font-family: var(--font-serif);
  font-size: 15px;
  line-height: 1.8;
}

.page-wrap { max-width: 860px; margin: 0 auto; padding: 0 16px 48px; }

/* ── Hero ── */
.hero-section {
  background: var(--color-bg-dark);
  color: #f5ede0;
  padding: 48px 24px 40px;
  text-align: center;
  margin-bottom: 32px;
}
.hero-name {
  font-size: 2rem;
  letter-spacing: .2em;
  color: var(--color-gold-light);
  margin-bottom: 8px;
}
.hero-birth {
  color: #c8b090;
  font-size: .9rem;
  margin-bottom: 12px;
}
.hero-tags { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-bottom: 16px; }
.hero-tag {
  background: rgba(201,151,58,.2);
  border: 1px solid rgba(201,151,58,.4);
  border-radius: 20px;
  padding: 3px 12px;
  font-size: .8rem;
  color: var(--color-gold-light);
}
.hero-quote {
  color: #d4b07a;
  font-size: .95rem;
  font-style: italic;
  max-width: 560px;
  margin: 0 auto;
}
.synastry-title { letter-spacing: .15em; }
.synastry-x { color: var(--color-gold); margin: 0 12px; }
.synastry-quote { margin-top: 12px; }

/* ── Section ── */
.report-section {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 24px 28px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
}
.section-title {
  font-size: 1rem;
  letter-spacing: .18em;
  color: var(--color-gold);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 8px;
  margin-bottom: 18px;
}

/* ── Pillars ── */
.pillars-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  justify-content: center;
}
.pillar {
  flex: 1;
  text-align: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px 8px;
  background: var(--color-bg-page);
}
.pillar-day { border-color: var(--color-gold); background: #fff8ec; }
.pillar-label { font-size: .75rem; color: var(--color-ink-muted); margin-bottom: 6px; }
.pillar-ganzhi { font-size: 1.3rem; letter-spacing: .05em; color: var(--color-ink); }

/* ── Bazi body ── */
.bazi-body { display: flex; gap: 24px; align-items: flex-start; }
.bazi-chart { flex: 0 0 200px; }
.bazi-analysis { flex: 1; }

/* ── Wuxing bars ── */
.wuxing-bars { display: flex; flex-direction: column; gap: 6px; }
.wx-bar-row { display: flex; align-items: center; gap: 8px; }
.wx-bar-label {
  width: 40px;
  font-size: .82rem;
  color: var(--color-ink-secondary);
  display: flex;
  align-items: center;
  gap: 3px;
}
.wx-bar-track {
  flex: 1;
  height: 8px;
  background: var(--color-border);
  border-radius: 4px;
  overflow: hidden;
}
.wx-bar-fill {
  height: 100%;
  width: 0;
  background: var(--wx-color);
  border-radius: 4px;
  transition: width 1s ease;
}
.wx-bar-val { width: 32px; font-size: .78rem; color: var(--color-ink-muted); text-align: right; }

/* ── Tags ── */
.tag { font-size: .68rem; padding: 1px 5px; border-radius: 3px; margin-left: 2px; }
.tag-absent  { background: #fbeaea; color: var(--color-accent-red); }
.tag-lucky   { background: #eaf3ee; color: var(--color-accent-jade); }
.tag-unlucky { background: #faf0e0; color: #8b6020; }

/* ── Analysis text ── */
.analysis-text { color: var(--color-ink); line-height: 1.9; }
.analysis-sub  { color: var(--color-ink-secondary); font-size: .88rem; margin-bottom: 8px; }

/* ── Bone ── */
.bone-header { display: flex; align-items: center; gap: 20px; margin-bottom: 16px; }
.bone-total { display: flex; align-items: baseline; gap: 4px; }
.bone-num { font-size: 2.2rem; color: var(--color-gold); font-weight: 600; }
.bone-unit { font-size: 1rem; color: var(--color-ink-secondary); }
.bone-rating { font-size: .9rem; color: var(--color-ink-secondary); font-weight: 600; }
.bone-breakdown { font-size: .78rem; color: var(--color-ink-muted); margin-top: 4px; }
.bone-poem {
  border-left: 3px solid var(--color-gold);
  padding: 12px 16px;
  margin: 16px 0;
  background: var(--color-bg-page);
  font-size: .92rem;
  line-height: 2;
  color: var(--color-ink-secondary);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.bone-interp { color: var(--color-ink); line-height: 1.9; }

/* ── Ziwei ── */
.ziwei-header { display: flex; align-items: center; gap: 20px; margin-bottom: 16px; flex-wrap: wrap; }
.ziwei-star-block { display: flex; flex-direction: column; align-items: center; }
.ziwei-star-label { font-size: .72rem; color: var(--color-ink-muted); }
.ziwei-star-name { font-size: 1.2rem; color: var(--color-gold); letter-spacing: .1em; }
.ziwei-pattern { color: var(--color-ink-secondary); font-size: .9rem; }
.empty-palace-note {
  background: #fff8e8;
  border-left: 3px solid var(--color-gold);
  padding: 8px 12px;
  margin-bottom: 12px;
  font-size: .85rem;
  color: #7a5a20;
}
.dayun-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px 16px;
  margin-bottom: 16px;
  background: var(--color-bg-page);
}
.dayun-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
.dayun-badge {
  background: var(--color-gold);
  color: #fff;
  font-size: .72rem;
  padding: 2px 8px;
  border-radius: 10px;
}
.dayun-age  { font-size: .88rem; color: var(--color-ink-secondary); }
.dayun-palace { font-size: .88rem; color: var(--color-ink); }
.dayun-interp { font-size: .88rem; color: var(--color-ink-secondary); }
.ziwei-analysis { margin-top: 8px; }

/* ── Western ── */
.signs-row { display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.sign-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 10px 16px;
  min-width: 80px;
}
.sign-icon { font-size: 1.4rem; margin-bottom: 4px; }
.sign-name-label { font-size: .68rem; color: var(--color-ink-muted); }
.sign-name { font-size: .9rem; color: var(--color-ink); }
.aspects-note { font-size: .85rem; color: var(--color-ink-secondary); margin-top: 8px; }

/* ── Name ── */
.name-header { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.name-strokes { font-size: .85rem; color: var(--color-ink-secondary); }
.name-sancai  { font-size: .85rem; color: var(--color-ink-secondary); }
.name-rating  { font-size: .85rem; font-weight: 600; padding: 2px 10px; border-radius: 10px; }
.rating-daji  { background: #eaf5ee; color: #2a6040; }
.rating-ji    { background: #eef8ea; color: #3a7020; }
.rating-zhongji { background: #f5f5ea; color: #5a6020; }
.rating-zhong { background: #f5f0e8; color: #6a5030; }
.rating-xiong { background: #faeaea; color: #8b2020; }
.wuge-row { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.wuge-item { display: flex; flex-direction: column; align-items: center; background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: var(--radius); padding: 8px 12px; }
.wuge-label  { font-size: .72rem; color: var(--color-ink-muted); margin-bottom: 2px; }
.wuge-num    { font-size: 1.25rem; font-weight: 600; color: var(--color-ink); line-height: 1.2; }
.wuge-name   { font-size: .75rem; color: var(--color-ink-secondary); margin-top: 2px; }
.wuge-elem   { font-size: .7rem;  color: var(--color-ink-muted); }
.wuge-rating { font-size: .72rem; font-weight: 600; margin-top: 2px; }
.name-score-row { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.name-score-label { font-size: .8rem; color: var(--color-ink-muted); white-space: nowrap; }
.name-score-bar-wrap { flex: 1; height: 8px; background: var(--color-border); border-radius: 4px; overflow: hidden; }
.name-score-bar { height: 100%; background: var(--color-gold); border-radius: 4px; transition: width .6s ease; }
.name-score-num { font-size: .95rem; font-weight: 700; color: var(--color-gold); white-space: nowrap; }
.name-score-rating { font-size: .8rem; white-space: nowrap; }
.sancai-block { font-size: .85rem; color: var(--color-ink-secondary); margin-bottom: 14px; line-height: 1.8; }
/* 六维度评分 */
.sixdim-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
@media (max-width: 600px) { .sixdim-grid { grid-template-columns: repeat(2, 1fr); } }
.sixdim-card { background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: var(--radius); padding: 12px 14px; }
.sixdim-title { font-size: .75rem; color: var(--color-ink-muted); letter-spacing: .08em; margin-bottom: 6px; }
.sixdim-score-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.sixdim-score-num { font-size: 1.4rem; font-weight: 700; color: var(--color-gold); }
.sixdim-score-max { font-size: .75rem; color: var(--color-ink-muted); }
.sixdim-bar-wrap { flex: 1; height: 6px; background: var(--color-border); border-radius: 3px; overflow: hidden; }
.sixdim-bar { height: 100%; border-radius: 3px; }
.sixdim-label { font-size: .75rem; font-weight: 600; margin-bottom: 4px; }
.sixdim-comment { font-size: .78rem; color: var(--color-ink-secondary); line-height: 1.7; }

/* ── Sketch ── */
.sketch-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.sketch-card {
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 14px;
}
.sketch-card-title { font-size: .75rem; color: var(--color-gold); letter-spacing: .12em; margin-bottom: 8px; }
.sketch-card p { font-size: .88rem; color: var(--color-ink); line-height: 1.8; }
.reconciliation-box {
  border: 1px solid var(--color-gold);
  border-radius: var(--radius);
  padding: 14px 18px;
  background: #fffbf0;
  margin-bottom: 12px;
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}
.reconciliation-label { font-size: .72rem; color: var(--color-gold); letter-spacing: .1em; white-space: nowrap; }
.reconciliation-text  { font-size: .92rem; color: var(--color-ink); font-style: italic; }
.mbti-note { background: var(--color-bg-page); border-left: 3px solid var(--color-purple); padding: 10px 14px; }
.mbti-label { font-size: .72rem; color: var(--color-purple); display: block; margin-bottom: 4px; }
.mbti-note p { font-size: .88rem; color: var(--color-ink-secondary); }

/* ── Confidence ── */
.conf-table { width: 100%; border-collapse: collapse; }
.conf-table th, .conf-table td { padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--color-border); }
.conf-table th { font-size: .78rem; color: var(--color-ink-muted); font-weight: normal; }
.conf-label { font-size: .88rem; }
.conf-stars { display: flex; gap: 2px; }
.conf-val   { font-size: .82rem; color: var(--color-ink-muted); }
.star-rating { display: inline-flex; gap: 2px; }
.star { width: 16px; height: 16px; }
.star-full   { fill: var(--color-gold); }
.star-empty  { fill: none; stroke: var(--color-gold); stroke-width: 1.5; }
.star-half   { }
.conf-notes { font-size: .82rem; color: var(--color-ink-muted); margin-top: 10px; }

/* ── Synastry ── */
.gauges-container { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; margin-bottom: 20px; }
.gauge-item { text-align: center; width: 180px; }
.gauge-svg  { width: 140px; height: 80px; }
.gauge-arc  { transition: stroke-dasharray 1.2s ease; }
.gauge-score { font-size: .85rem; fill: var(--color-ink); font-family: var(--font-serif); }
.gauge-label { font-size: .82rem; color: var(--color-ink-secondary); margin-top: 4px; }
.gauge-sublabel { font-size: .72rem; color: var(--color-ink-muted); }
.dim-descriptions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.dim-desc h4 { font-size: .82rem; color: var(--color-gold); margin-bottom: 6px; }
.dim-desc p  { font-size: .85rem; color: var(--color-ink-secondary); }

.comparison-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.summary-card {
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
}
.sum-name  { font-size: 1rem; color: var(--color-gold); margin-bottom: 4px; }
.sum-meta  { font-size: .8rem; color: var(--color-ink-muted); margin-bottom: 12px; }
.sum-ziwei { font-size: .85rem; color: var(--color-ink-secondary); margin: 8px 0 4px; }
.sum-dayun { font-size: .8rem;  color: var(--color-ink-muted); }
.sum-signs { font-size: .82rem; color: var(--color-ink-secondary); margin: 8px 0; }
.sum-inner { font-size: .82rem; color: var(--color-ink-secondary); line-height: 1.7; margin-top: 8px; }
.full-detail { margin-top: 12px; }
.full-detail summary { font-size: .8rem; color: var(--color-gold); cursor: pointer; }

.total-score-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 20px; }
.total-label { font-size: .88rem; color: var(--color-ink-secondary); }
.total-num   { font-size: 2.4rem; color: var(--color-gold); font-weight: 600; }
.total-denom { font-size: 1rem; color: var(--color-ink-muted); }
.total-stars { font-size: 1rem; color: var(--color-gold); margin-left: 8px; }
.score-bars  { display: flex; flex-direction: column; gap: 10px; }
.score-bar-row { display: flex; align-items: center; gap: 10px; }
.score-bar-label { width: 110px; font-size: .82rem; color: var(--color-ink-secondary); flex-shrink: 0; }
.score-bar-track { flex: 1; height: 10px; background: var(--color-border); border-radius: 5px; overflow: hidden; }
.score-bar-fill  { height: 100%; width: 0; background: var(--bar-color, var(--color-gold)); border-radius: 5px; transition: width 1.2s cubic-bezier(.4,0,.2,1); }
.score-bar-value { width: 48px; font-size: .8rem; color: var(--color-ink-muted); text-align: right; flex-shrink: 0; }

.overall-card { background: var(--color-bg-page); border-left: 3px solid var(--color-gold); padding: 16px 20px; }
.overall-card p { line-height: 1.9; color: var(--color-ink); }

.scenario-tabs  { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.scenario-tab   { background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 20px; padding: 5px 14px; font-size: .82rem; cursor: pointer; color: var(--color-ink-secondary); font-family: var(--font-serif); transition: all .2s; }
.scenario-tab:hover, .scenario-tab.active { background: var(--color-gold); color: #fff; border-color: var(--color-gold); }
.scenario-content p { font-size: .9rem; color: var(--color-ink); line-height: 1.9; }

.full-person-details { margin-bottom: 12px; }
.full-person-summary { font-size: .9rem; color: var(--color-gold); cursor: pointer; padding: 8px 0; }
.full-person-inner { margin-top: 12px; }

/* ── Footer ── */
.page-footer {
  text-align: center;
  padding: 24px 0 12px;
  font-size: .78rem;
  color: var(--color-ink-muted);
  border-top: 1px solid var(--color-border);
  margin-top: 32px;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .bazi-body { flex-direction: column; }
  .bazi-chart { flex: none; width: 100%; }
  .sketch-cards { grid-template-columns: 1fr; }
  .comparison-grid { grid-template-columns: 1fr; }
  .dim-descriptions { grid-template-columns: 1fr; }
  .gauges-container { gap: 12px; }
  .pillars-row { gap: 6px; }
  .pillar-ganzhi { font-size: 1rem; }
}
"""

_JS = """
document.addEventListener('DOMContentLoaded', () => {
  // 进度条动画（IntersectionObserver）
  const fillEls = document.querySelectorAll('.wx-bar-fill, .score-bar-fill, .gauge-arc');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(el => {
      if (el.isIntersecting) {
        const target = el.target;
        if (target.classList.contains('wx-bar-fill') || target.classList.contains('score-bar-fill')) {
          const pct = target.style.getPropertyValue('--wx-pct') || target.style.getPropertyValue('--bar-pct');
          if (pct) target.style.width = pct;
        }
        observer.unobserve(target);
      }
    });
  }, { threshold: 0.1 });
  fillEls.forEach(el => observer.observe(el));

  // 场景 Tab 切换
  document.querySelectorAll('.scenario-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.scenario-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.scenario-content').forEach(c => c.hidden = true);
      tab.classList.add('active');
      const panel = document.getElementById(tab.dataset.target);
      if (panel) panel.hidden = false;
    });
  });
});
"""


def render_html(ctx: dict) -> str:
    meta = ctx.get("meta", {})
    title = meta.get("title", "天机命理报告")
    generated_at = meta.get("generated_at", datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        gen_str = dt.strftime("%Y年%m月%d日 %H:%M")
    except Exception:
        gen_str = generated_at

    scene = meta.get("scene", "personal")
    if scene == "synastry":
        body_content = build_synastry_page(ctx)
    else:
        body_content = build_personal_page(ctx)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} · 天机</title>
  <style>{_CSS}</style>
</head>
<body>
<div class="page-wrap">
{body_content}
<footer class="page-footer">
  天机命理报告 · 生成时间 {gen_str} · 仅供参考，命理学并非精确科学
</footer>
</div>
<script>{_JS}</script>
</body>
</html>"""


# ════════════════════════════════════════════════════════
# 模块 5：CLI 入口
# ════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="天机 v8.0 HTML 报告渲染器")
    parser.add_argument("--reading", default="reading.json",        help="reading.json 路径")
    parser.add_argument("--chart",   default="chart.json",          help="chart.json 路径（可选）")
    parser.add_argument("--output",  default="tianji_report.html",  help="输出 HTML 路径")
    args = parser.parse_args()

    reading = load_reading(args.reading)
    chart   = load_chart(args.chart)
    ctx     = merge_data(reading, chart)
    html    = render_html(ctx)

    Path(args.output).write_text(html, encoding="utf-8")
    size_kb = Path(args.output).stat().st_size / 1024
    print(f"[天机] 报告已生成：{args.output}（{size_kb:.1f} KB）")


if __name__ == "__main__":
    main()
