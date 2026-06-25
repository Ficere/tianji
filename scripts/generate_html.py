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
    reconciliation = sketch.get("reconciliation_theme", "") or sketch.get("reconciliation", "")

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

    # ── 基础数据 ─────────────────────────────────────────────
    life_palace      = zw.get("life_palace", "")
    life_star        = zw.get("life_palace_star", "")
    body_palace      = zw.get("body_palace", "")
    wuxing_ju        = zw.get("wuxing_ju", "")
    life_master      = zw.get("life_master", "")
    body_master      = zw.get("body_master", "")
    dayun_dir        = zw.get("dayun_direction", "顺行")
    pattern          = zw.get("pattern", "")
    overall          = zw.get("overall_analysis", "")

    palace_stars = zw.get("twelve_palaces_stars", {})
    palace_zhi   = zw.get("twelve_palaces_zhi", {})
    sihua_detail = zw.get("sihua_detail", {})
    dayun_seq    = zw.get("dayun_sequence", [])
    current_dayun = zw.get("current_dayun", {})
    current_age_range = current_dayun.get("age_range", "")
    palace_readings = zw.get("palace_readings", {})

    # ── 四化星标记 ───────────────────────────────────────────
    sihua_mark = {}
    sihua_colors = {"化禄": "#c9973a", "化权": "#c0392b", "化科": "#2980b9", "化忌": "#7f8c8d"}
    for tag, info in sihua_detail.items():
        star = info.get("星曜", "")
        if star:
            sihua_mark.setdefault(star, []).append(tag)

    MAIN_STARS = {
        "紫微","天机","太阳","武曲","天同","廉贞",
        "天府","太阴","贪狼","巨门","天相","天梁","七杀","破军"
    }

    def classify_stars(stars):
        main, aux = [], []
        for s in stars:
            (main if s in MAIN_STARS else aux).append(s)
        return main, aux

    def star_badge(s, small=False):
        tags = sihua_mark.get(s, [])
        suffix = ""
        for t in tags:
            col = sihua_colors.get(t, "#888")
            suffix += f'<span class="ziwei-sihua-tag" style="background:{col}">{t[1]}</span>'
        cls = "ziwei-star-badge-sm" if small else "ziwei-star-badge"
        return f'<span class="{cls}">{s}{suffix}</span>'

    # ── 十二宫网格 ───────────────────────────────────────────
    PALACE_ORDER = [
        "命宫","兄弟宫","夫妻宫","子女宫",
        "财帛宫","疾厄宫","迁移宫","交友宫",
        "官禄宫","田宅宫","福德宫","父母宫"
    ]

    # ── 对宫映射（六对宫）──────────────────────────────────────
    OPPOSITE = {
        "命宫":"迁移宫","迁移宫":"命宫",
        "兄弟宫":"交友宫","交友宫":"兄弟宫",
        "夫妻宫":"官禄宫","官禄宫":"夫妻宫",
        "子女宫":"田宅宫","田宅宫":"子女宫",
        "财帛宫":"福德宫","福德宫":"财帛宫",
        "疾厄宫":"父母宫","父母宫":"疾厄宫",
    }

    def get_opposite_main_stars(pname):
        """返回对宫的主星列表"""
        opp = OPPOSITE.get(pname, "")
        if not opp:
            return []
        opp_stars = palace_stars.get(opp, [])
        main, _ = classify_stars(opp_stars)
        return main, opp

    def render_palace_cell(pname):
        zhi   = palace_zhi.get(pname, "")
        stars = palace_stars.get(pname, [])
        main, aux = classify_stars(stars)
        is_life = (pname == "命宫")
        body_ref = body_palace or ""
        is_body = ("福德宫" in pname and "福德" in body_ref) or \
                  ("亥宫" in body_ref and "福德" in pname)
        is_curr_dayun = current_dayun.get("palace", "") == pname
        has_reading   = pname in palace_readings
        is_empty      = len(main) == 0  # 无主星 = 空宫

        cell_class = "ziwei-cell"
        if is_life:        cell_class += " cell-life"
        if is_body:        cell_class += " cell-body"
        if is_curr_dayun:  cell_class += " cell-curr-dayun"
        if has_reading:    cell_class += " cell-has-reading"
        if is_empty:       cell_class += " cell-empty"

        markers = ""
        if is_life:       markers += '<span class="cell-marker marker-life">命</span>'
        if is_body:       markers += '<span class="cell-marker marker-body">身</span>'
        if is_curr_dayun: markers += '<span class="cell-marker marker-dayun">限</span>'

        # 空宫：显示「借对宫」提示
        if is_empty:
            opp_main, opp_name = get_opposite_main_stars(pname)
            if opp_main:
                opp_stars_str = "·".join(opp_main)
                main_html = (
                    f'<span class="ziwei-empty-cell">空宫</span>'
                    f'<span class="borrow-hint">借{opp_name} {opp_stars_str}</span>'
                )
            else:
                main_html = '<span class="ziwei-empty-cell">空宫</span>'
        else:
            main_html = "".join(star_badge(s) for s in main)

        aux_html  = "".join(star_badge(s, small=True) for s in aux)
        aux_block = f'<div class="cell-aux-stars">{aux_html}</div>' if aux else ""

        return (
            f'<div class="{cell_class}">'
            f'<div class="cell-header">'
            f'<span class="cell-zhi">{zhi}</span>'
            f'<span class="cell-name">{pname}</span>'
            f'{markers}</div>'
            f'<div class="cell-main-stars">{main_html}</div>'
            f'{aux_block}'
            f'</div>'
        )

    grid_cells = "\n".join(render_palace_cell(p) for p in PALACE_ORDER)

    # ── 空宫对宫关系面板 ─────────────────────────────────────
    def render_empty_palace_panel():
        # ── 主星核心特质词库 ─────────────────────────────────
        # 每颗主星：(核心能量, 优势面, 风险面)
        STAR_TRAITS = {
            "紫微": ("权威与尊贵", "天然领导力加持，资源与人脉自然向其聚拢", "容易依赖外部认可，主动性不足时等待机遇"),
            "天机": ("智谋与变动", "机敏灵活，善于借势，遇事能找到出路", "想法多但难以持续深耕，方向感需主动锚定"),
            "太阳": ("光热与外向", "阳性能量充足，社会能见度高，易得贵人", "能量外放多内收少，需注意个人边界与消耗"),
            "武曲": ("果断与财气", "行动力强，财务嗅觉敏锐，能在竞争中立足", "刚硬有余柔韧不足，人际上容易显得强势"),
            "天同": ("温和与享受", "平和包容，抗压力强，不急于一时", "进取心弱，容易满足于现状而错失突破窗口"),
            "廉贞": ("才华与波动", "文艺气质与执行力兼备，适合创造性领域", "情绪波动影响稳定性，需建立规律的节奏感"),
            "天府": ("稳健与积累", "厚积薄发，擅长守成与资源管理", "偏保守，新事物适应慢，需要主动突破舒适区"),
            "太阴": ("感性与内敛", "细腻直觉强，长于经营关系与财务", "情绪敏感，易受外部情绪感染，需要安全感支撑"),
            "贪狼": ("欲望与魅力", "多才多艺，魅力外放，吸引力强", "欲望分散难以深耕，容易被诱惑拖离主线"),
            "巨门": ("口才与审视", "思维深刻，善于辨析，言语穿透力强", "多疑的底色容易产生内耗，也易引发误解"),
            "天相": ("辅佐与规则", "重视秩序，执行力稳，善于协调", "个人主见偏弱，需要依托强势主星才能充分发挥"),
            "天梁": ("守护与原则", "正直担当，有长辈缘与贵人运", "固执于原则有时变为刻板，难以变通"),
            "七杀": ("杀伐与突破", "推进力极强，敢于破局，执行果决", "结构性孤独感重，冲突概率高，需主动建立支持系统"),
            "破军": ("变革与开创", "颠覆性强，擅长从零到一的突破", "破坏旧有结构后需警惕「破而不立」，稳定性需刻意经营"),
        }

        # ── 空宫所属领域的借宫逻辑模板 ────────────────────────
        # {空宫} 借 {对宫} {主星} → 该宫位领域如何被影响
        PALACE_CONTEXT = {
            "命宫":  ("先天性格底色由{opp}主星塑造", "人格灵活、易受外部环境映射"),
            "迁移宫":("外部际遇与社会能见度受{opp}能量辐射", "主动出击的效果大于守株待兔"),
            "财帛宫":("财富动能由{opp}的能量决定", "财源依赖外部机缘，经营意识比先天资质更关键"),
            "福德宫":("精神世界与内在满足感受{opp}主星塑造", "内心富足感与外部所得有深度关联"),
            "官禄宫":("事业格局由{opp}主星的能量映射进来", "关键人际关系是事业最大的变量"),
            "夫妻宫":("亲密关系的缘分结构受{opp}主星折射", "对方的特质对自身发展影响深远，选人比经营更重要"),
            "兄弟宫":("手足与平辈关系由{opp}主星映射", "社会网络的质量弥补了血缘连结的弱化"),
            "交友宫":("朋友圈能量结构由{opp}主星定调", "亲密关系的深度决定了外部人脉资源的厚度"),
            "子女宫":("子女缘与创造力受{opp}主星影响", "家庭环境与内在安全感是创造力的实质土壤"),
            "田宅宫":("家宅与不动产运势由{opp}主星牵引", "家庭格局的扩展往往是资产积累的触发器"),
            "疾厄宫":("体质底色与健康节律受{opp}主星映射", "早年养育方式与情绪模式对身体有长期影响"),
            "父母宫":("长辈缘与原生家庭结构由{opp}主星反射", "与父母关系的质量在健康与心理层面互为镜像"),
        }

        def build_dynamic_desc(pname, opp_name, opp_main):
            """根据空宫领域 + 对宫实际主星，生成专属动态文案"""
            ctx_tmpl, ctx_suffix = PALACE_CONTEXT.get(pname, ("受{opp}主星影响", ""))
            ctx_prefix = ctx_tmpl.format(opp=opp_name)

            if not opp_main:
                return f"{ctx_prefix}；对宫亦为空宫，该领域受流年大限的动态主星牵引，灵活性极高。"

            # 主星解读：取第一颗（最主要）；若有两颗取前两颗
            descs = []
            for star in opp_main[:2]:
                trait = STAR_TRAITS.get(star)
                if trait:
                    core, advantage, risk = trait
                    descs.append(f"{star}（{core}）带来{advantage}，同时{risk}")

            if descs:
                star_desc = "；".join(descs)
                # 四化标注：检查对宫主星是否有四化
                sihua_notes = []
                for star in opp_main[:2]:
                    tags = sihua_mark.get(star, [])
                    if tags:
                        sihua_notes.append(f"{star}{'/'.join(tags)}")
                sihua_str = ""
                if sihua_notes:
                    sihua_str = f"注意{'/'.join(sihua_notes)}落此，能量更为显化。"
                return f"{ctx_prefix}：{star_desc}。{ctx_suffix}{'　' if ctx_suffix else ''}{sihua_str}".strip()
            else:
                return f"{ctx_prefix}。{ctx_suffix}"

        # ── 正式渲染 ──────────────────────────────────────────
        items = []
        for pname in PALACE_ORDER:
            stars = palace_stars.get(pname, [])
            main, _ = classify_stars(stars)
            if len(main) > 0:
                continue
            opp_main, opp_name = get_opposite_main_stars(pname)
            opp_str = "·".join(opp_main) if opp_main else "亦空宫"
            pr = palace_readings.get(pname, {})
            reading = pr.get("reading", "") if pr else ""
            reading_short = reading[:60] + "…" if len(reading) > 60 else reading

            desc = build_dynamic_desc(pname, opp_name, opp_main)
            reading_html = f'<div class="ep-reading">{reading_short}</div>' if reading_short else ""
            items.append(
                f'<div class="empty-palace-item">'
                f'<div class="ep-header">'
                f'<span class="ep-name">{pname}</span>'
                f'<span class="ep-arrow">→ 借</span>'
                f'<span class="ep-opp">{opp_name}</span>'
                f'<span class="ep-stars">{opp_str}</span>'
                f'</div>'
                f'<div class="ep-desc">{desc}</div>'
                f'{reading_html}'
                f'</div>'
            )
        if not items:
            return ""
        return (
            f'<div class="empty-palace-panel">'
            f'<div class="ep-panel-title">空宫借对宫说明</div>'
            f'{"".join(items)}'
            f'</div>'
        )

    empty_panel_html = render_empty_palace_panel()

    # ── 四化卡片 ─────────────────────────────────────────────
    sihua_card_defs = [
        ("化禄","#c9973a","禄","财源·流动·吉运","事业与财运的顺势助力，所在宫位有积累或机遇"),
        ("化权","#c0392b","权","权势·控制·决断","强势能量加持，所在宫位主导权增强，也带来张力"),
        ("化科","#2980b9","科","声誉·智慧·贵气","名声与才华加持，所在宫位有文昌之气"),
        ("化忌","#7f8c8d","忌","功课·阻碍·反复","一生反复的课题，所在宫位需要主动经营"),
    ]

    def render_sihua_card(tag, color, short, meaning, desc):
        info   = sihua_detail.get(tag, {})
        star   = info.get("星曜", "—")
        zhi    = info.get("所在地支", "—")
        palace = info.get("所在宫位", "—")
        pr     = palace_readings.get(palace, {})
        pr_txt = pr.get("reading", "") if pr else ""
        snippet = (pr_txt[:80] + "…") if len(pr_txt) > 80 else pr_txt
        snip_html = f'<div class="sihua-palace-snippet">「{palace}」：{snippet}</div>' if snippet else ""
        return (
            f'<div class="sihua-card" style="border-left:3px solid {color}">'
            f'<div class="sihua-card-header">'
            f'<span class="sihua-badge" style="background:{color}">{short}</span>'
            f'<span class="sihua-tag-name" style="color:{color}">{tag}</span>'
            f'<span class="sihua-star">→ {star}</span>'
            f'<span class="sihua-palace">落 {palace}（{zhi}宫）</span>'
            f'</div>'
            f'<div class="sihua-meaning">{meaning}</div>'
            f'<div class="sihua-desc">{desc}</div>'
            f'{snip_html}'
            f'</div>'
        )

    sihua_cards_html = "\n".join(
        render_sihua_card(tag, color, short, meaning, desc)
        for tag, color, short, meaning, desc in sihua_card_defs
        if tag in sihua_detail
    )

    # ── 大限时间轴 ────────────────────────────────────────────
    def render_dayun_timeline():
        items = []
        for d in dayun_seq:
            rng    = d.get("年龄范围", "")
            palace = d.get("宫位", "")
            zhi    = d.get("地支", "")
            stars  = d.get("主星", [])
            stars_str = "·".join(stars) if stars else "空宫"
            is_curr = (rng == current_age_range)
            cls = "dayun-item dayun-curr" if is_curr else "dayun-item"
            curr_lbl = '<span class="dayun-curr-tag">▶ 当前</span>' if is_curr else ""
            items.append(
                f'<div class="{cls}">'
                f'<div class="dayun-rng">{rng}{curr_lbl}</div>'
                f'<div class="dayun-dot"></div>'
                f'<div class="dayun-info">'
                f'<span class="dayun-palace-nm">{palace}</span>'
                f'<span class="dayun-zhi-nm">（{zhi}）</span>'
                f'<span class="dayun-stars-nm">{stars_str}</span>'
                f'</div></div>'
            )
        return f'<div class="dayun-timeline">{"".join(items)}</div>'

    timeline_html = render_dayun_timeline()

    curr_interp = current_dayun.get("interpretation", "")
    if curr_interp:
        cp = current_dayun.get("palace", "")
        cs = current_dayun.get("star", "")
        curr_dayun_detail = (
            f'<div class="curr-dayun-detail">'
            f'<div class="curr-dayun-label">当前大限深度解读 · {current_age_range} · {cp} · {cs}</div>'
            f'<p class="curr-dayun-text">{curr_interp}</p>'
            f'</div>'
        )
    else:
        curr_dayun_detail = ""

    # ── 六宫深度解读 ──────────────────────────────────────────
    SIX_PALACES = ["命宫","财帛宫","官禄宫","夫妻宫","疾厄宫","迁移宫"]
    SIX_ICONS   = {"命宫":"☯","财帛宫":"◈","官禄宫":"▲","夫妻宫":"♡","疾厄宫":"◉","迁移宫":"◎"}
    SIX_SUBS    = {
        "命宫":"先天人格底色","财帛宫":"财富结构",
        "官禄宫":"事业格局","夫妻宫":"亲密关系",
        "疾厄宫":"健康倾向","迁移宫":"外部环境"
    }

    # 宫位视角句式模板：宫名 → 该领域核心问题
    PALACE_QUESTION = {
        "命宫":  "这个人本质上是谁？驱动力从哪里来？",
        "财帛宫":"财富从哪里来，又容易从哪里漏出去？",
        "官禄宫":"事业上天然擅长什么，又容易在哪里卡住？",
        "夫妻宫":"亲密关系里他/她需要什么，又会带入什么结构性问题？",
        "疾厄宫":"身体和能量管理的盲区在哪里？",
        "迁移宫":"在外部世界、陌生环境中，他/她呈现什么能量？",
    }

    # 主星在各宫位的核心关键词（优势面，风险面，行动建议）
    STAR_IN_PALACE = {
        # (星, 宫) → (优势, 风险, 建议)
        ("紫微","命宫"):  ("气场天成，自带领导力，决策有主见","过度自我，难以接受反馈，孤独感重","主动建立反馈机制，允许他人挑战自己"),
        ("紫微","官禄宫"):("事业心强，适合独当一面，有整合资源的本能","容易以自我为中心，忽略团队协作","刻意培养授权能力，接受「不完美但高效」的执行"),
        ("紫微","夫妻宫"):("对伴侣有高标准，亲密关系稳重","对等关系难，强势易压制对方","选择强独立性伴侣，避免形成控制-依附结构"),
        ("紫微","迁移宫"):("在外场合气场出众，贵人缘佳","不主动开拓时容易等待机会上门","主动社交比等待机遇更有效"),
        ("天机","命宫"):  ("思维活跃，善分析，适应力强","想多行少，容易原地分析瘫痪","给自己设定「分析截止时间」，强制执行"),
        ("天机","官禄宫"):("策略型人才，适合顾问、规划类工作","频繁变更方向，难以深耕","择一方向专注3年以上，用深度换竞争壁垒"),
        ("太阳","命宫"):  ("热情外放，能量感染力强，天然聚焦点","自我消耗过大，容易燃尽","定期关机补能，区分「我真正想要」与「我想让别人看到」"),
        ("太阳","官禄宫"):("适合舞台型、外部曝光类职业，上进心强","虚荣心影响决策，在意他人评价","建立内驱型目标系统，减少外部评价的权重"),
        ("太阳","财帛宫"):("能量大，创造财富速度快，慷慨","支出同样大，守财能力弱","收入10-20%强制锁仓，避免月光习惯"),
        ("武曲","命宫"):  ("意志坚定，财气天生，执行力强","情感表达偏弱，给人强硬冷漠感","主动表达柔软面，减少不必要的刚性对立"),
        ("武曲","财帛宫"):("正财运佳，踏实积累型","偏财运弱，投机类风险大","走稳健积累路线，避开高风险投机"),
        ("武曲","官禄宫"):("适合金融、工程、管理类，执行力出众","与团队摩擦多，独断易失人心","主动倾听不同意见，不必每次都赢"),
        ("天同","命宫"):  ("心态平和，压力耐受力强，适应性好","进取心不足，容易将就","定期重新审视目标，防止「差不多就好」惰性"),
        ("天同","夫妻宫"):("亲密关系平和，少剧烈冲突","关系缺乏张力，容易平淡","主动创造新鲜感，关系维护需要刻意经营"),
        ("廉贞","命宫"):  ("才华横溢，热情有创造力，执行力强","情绪波动大，易冲动决策","建立冷静期机制：重大决定睡一觉再执行"),
        ("廉贞","官禄宫"):("适合需要激情和创意的职业","情绪化影响职业稳定性","用流程和规律对冲情绪波动"),
        ("天府","命宫"):  ("稳健、守成能力强，逢凶化吉","过于保守，错失突破机会","每年主动做一件「不确定但有潜力」的事"),
        ("天府","夫妻宫"):("亲密关系稳定，有安全感","太稳容易无聊，对方可能感到被限制","给关系留白，接受伴侣的独立空间"),
        ("太阴","命宫"):  ("细腻敏感，直觉强，感受力丰富","情绪内耗重，自我批判多","建立情绪记录习惯，将内耗转化为创作或行动"),
        ("太阴","财帛宫"):("女性财缘佳，靠积累和理财","财运波动受情绪影响","财务决策与情绪分离，固定时间做理财复盘"),
        ("贪狼","命宫"):  ("魅力四射，全方位好奇心，欲望感旺盛","方向分散，什么都想要导致什么都不深","每年只深耕一个主方向，其余保持浅层探索"),
        ("贪狼","官禄宫"):("适合需要人际魅力的行业，人脉广","事业线可能过多，难以聚焦","给事业划定「主赛道」，把社交能力导入一个核心方向"),
        ("巨门","命宫"):  ("口才好，善于表达，分析能力强","话多招是非，容易在言语上树敌","说话前问自己「说了对谁有好处」，减少不必要的评论"),
        ("天相","命宫"):  ("做事细心，有规矩感，亲和力好","主动性不足，依赖他人推动","主动承担发起者角色，锻炼独立启动能力"),
        ("天梁","命宫"):  ("慈悲心重，有责任感，贵人缘好","太愿意扛事，容易过劳","学会说「不」，区分哪些责任是真正属于自己的"),
        ("七杀","命宫"):  ("行动力超强，敢破局，意志坚","结构性孤独，冲突多，容易让自己四面树敌","主动建立支持系统，不必每次都单打独斗"),
        ("七杀","官禄宫"):("适合需要开拓和决断的岗位，天然领导者","团队关系紧张，容易失去核心骨干","投资在人际关系维护上，管理者要留住人不只是推进事"),
        ("破军","命宫"):  ("改革气质，敢于从零开始，创新力强","破坏旧有结构后，建立新秩序的耐心不足","每次「破」之前先规划「立」，不做无目的的颠覆"),
        ("破军","财帛宫"):("有开创财富的能力，但财富波动大","冒进导致财务风险","给自己设资金安全底线，底线以上才可冒进"),
        ("破军","官禄宫"):("适合创业、颠覆性行业，天然变革者","稳定性差，频繁跳槽或转型","在开创期确认自己想建立什么，而不只是打破什么"),
        # ── 夫妻宫补充 ──
        ("太阳","夫妻宫"):  ("感情热情外放，伴侣往往有光彩","男性贵人缘化忌时感情是功课，容易消耗","把化忌当成「感情需要主动经营」的提示，而非不吉兆头"),
        ("破军","夫妻宫"):  ("感情有开创力，伴侣往往带来新局面","感情路波折多，容易「破而不立」","每段关系结束前先弄清楚自己真正需要什么"),
        ("天机","夫妻宫"):  ("感情聪明多变，善于理解伴侣","想法多、变化快，伴侣容易感到捉摸不定","建立感情里的「稳定仪式」，减少随意变化带来的不安全感"),
        ("廉贞","夫妻宫"):  ("感情热烈有激情","情绪化影响亲密关系稳定性","高情绪时暂缓重大感情决定，冷静24小时再行动"),
        ("武曲","夫妻宫"):  ("感情务实稳定，有担当","情感表达刚硬，伴侣容易感到被忽视","主动增加情感表达频率，不要让伴侣猜"),
        ("天梁","夫妻宫"):  ("伴侣往往有长者特质或成熟稳重","感情偏不对等，容易成为被照顾或照顾的一方","寻找平等型伴侣，注意关系是否健康对等"),
        ("太阴","夫妻宫"):  ("感情细腻温柔，重视内在连接","感情内耗重，容易把感情当成情绪垃圾桶","建立独立的情绪管理通道，不把所有压力带进亲密关系"),
        ("贪狼","夫妻宫"):  ("感情魅力强，性吸引力旺","容易花心或被多人吸引，感情专一度需刻意维护","把贪狼的探索欲投入到关系深度上，而不是关系数量"),
        ("巨门","夫妻宫"):  ("感情中口才好，善于表达","话多易引发口角，言语是感情最大的杀伤武器","练习「说之前想三秒」，感情里的话比工作里更有杀伤力"),
        ("天相","夫妻宫"):  ("感情稳定，有规矩感和安全感","缺乏主动，依赖对方推动感情进展","主动发起约会和关键对话，不要等对方先动"),
        # ── 迁移宫补充 ──
        ("七杀","迁移宫"):  ("在外竞争力强，敢于闯荡陌生领域","外部环境摩擦多，容易遭遇对抗与孤立","把外部压力当磨刀石，同时主动建立在外的支持网络"),
        ("天机","迁移宫"):  ("外部适应力强，善于在变化中找机会","在外容易多变，被人视为不稳定","在外部展示自己时，突出一个核心定位，减少「什么都能做」的印象"),
        ("太阳","迁移宫"):  ("在外形象光鲜，易受注目，贵人多","消耗大，在外用力过猛","给自己设定「外部能量消耗上限」，保留内部恢复时间"),
        ("廉贞","迁移宫"):  ("在外才华横溢，创意表现力强","情绪在外部场合容易失控","建立公开场合的情绪缓冲机制，不让即时情绪影响外部形象"),
        ("武曲","迁移宫"):  ("在外果决有担当，财气好","在外太刚，容易给人强硬难接近的印象","在外部场合主动展示柔软一面，比刚硬更能赢得合作"),
        ("贪狼","迁移宫"):  ("在外魅力十足，社交圈广","在外精力分散，难以聚焦","出门前设定本次外部互动的核心目标，避免被新鲜感带跑"),
        # ── 财帛宫补充 ──
        ("天机","财帛宫"):  ("财运灵活多变，善于找到财富机会","财来财去，稳定积累能力弱","给自己设「财富不动仓」：每笔收入固定比例锁死不动"),
        ("廉贞","财帛宫"):  ("财运有爆发力，敢于投入","情绪化影响财务决策","大额财务决策强制等待72小时再执行"),
        ("天同","财帛宫"):  ("财运平和，不太缺钱但也不会大富","进取心弱，容易满足于够用","定期审视财务目标是否已经过时"),
        ("天梁","财帛宫"):  ("贵人财缘好，有偏财运","守财能力弱，容易把钱送人","建立清晰的财务边界，区分「我愿意给」和「被要求给」"),
        ("太阴","财帛宫"):  ("女性财缘佳，靠积累和理财","财运波动受情绪影响","财务决策时问自己：我是在满足情绪需求还是理性需求"),
        ("天相","财帛宫"):  ("财运稳健，有守财天赋","过于保守，错失增值机会","给财务配置10-20%的「成长型仓位」"),
        ("天府","财帛宫"):  ("守财聚财能力极强，资产稳健","财运过于保守，难以突破","接受适度风险是财富成长的必要成本"),
        ("七杀","财帛宫"):  ("财运有爆发力，适合独立创业积累","财富波动大，赚多散多","在高收入期主动建立固定资产仓位"),
        ("天梁","官禄宫"):  ("适合学术、政策、顾问类职业，贵人缘极佳","事业依赖贵人，独立创业难","主动经营贵人关系，但同时培养独立决策能力"),
        ("天相","官禄宫"):  ("工作细心负责，做事有规矩，受上司信任","主动性不足，等待被安排","培养主动提案的习惯，不只是执行者也要成为发起者"),
        ("太阴","官禄宫"):  ("适合后台支撑、创意类、女性向行业","在强竞争环境里容易压力过大","找到能发挥细腻特质的工作环境，不必强迫自己成为猛将"),
        ("天同","官禄宫"):  ("工作环境平和，不爱竞争","事业进取心弱，容易原地踏步","定期强制给自己设定跳出舒适区的工作目标"),
        ("贪狼","财帛宫"):  ("财运活跃，多元化收入机会多","花钱和赚钱一样猛，净积累慢","设立「欲望账户」：把冲动消费锁进专门账户限额管理"),
    }

    # 四化标注：检查该宫位是否有四化落入
    def get_sihua_in_palace(pname):
        tags = []
        for tag, info in sihua_detail.items():
            if info.get("所在宫位") == pname:
                star = info.get("星曜", "")
                color_map = {"化禄":"#c9973a","化权":"#c0392b","化科":"#2980b9","化忌":"#7f8c8d"}
                color = color_map.get(tag, "#888")
                tags.append((tag, star, color))
        return tags

    def render_prc(pname):
        pr = palace_readings.get(pname, {})
        if not pr:
            return ""
        stars_list = pr.get("stars", [])
        zhi_c   = pr.get("zhi", "")
        reading = pr.get("reading", "")
        main, aux = classify_stars(stars_list)
        stars_html = "".join(star_badge(s) for s in main)
        stars_html += "".join(star_badge(s, small=True) for s in aux)
        icon = SIX_ICONS.get(pname, "◆")
        sub  = SIX_SUBS.get(pname, "")
        question = PALACE_QUESTION.get(pname, "")

        # 四化标注
        sihua_in = get_sihua_in_palace(pname)
        sihua_tags_html = ""
        for tag, star, color in sihua_in:
            sihua_tags_html += (
                f'<span class="prc-sihua-tag" style="background:{color};color:#fff;'
                f'font-size:.7rem;padding:1px 6px;border-radius:3px;margin-left:4px">'
                f'{tag[1:]}↓{star}</span>'
            )

        # 动态组合分析
        combo_blocks = []
        for s in main:
            key = (s, pname)
            if key in STAR_IN_PALACE:
                adv, risk, action = STAR_IN_PALACE[key]
                combo_blocks.append(
                    f'<div class="prc-combo">'
                    f'<div class="prc-combo-star">{s}</div>'
                    f'<div class="prc-combo-content">'
                    f'<span class="prc-adv">✦ {adv}</span>'
                    f'<span class="prc-risk">⚠ {risk}</span>'
                    f'<span class="prc-action">→ {action}</span>'
                    f'</div></div>'
                )

        # 如果有多颗主星，加组合说明
        combo_note = ""
        if len(main) >= 2:
            pair_notes = {
                frozenset(["太阳","破军"]): "太阳·破军同宫：创造力与执行力高度结合，开拓型能量强，但消耗极大，需要充足的恢复时间",
                frozenset(["天同","天府"]): "天同·天府同宫：平稳享受型结构，极少冲突，但进取心偏弱，需主动设置外部压力源",
                frozenset(["紫微","天府"]): "紫微·天府同宫：顶级稳健格局，守成积累能力极强，适合长线布局",
                frozenset(["廉贞","巨门"]): "廉贞·巨门同宫：口才型才华，适合表达类职业，但情绪管理是核心课题",
                frozenset(["太阳","贪狼"]): "太阳·贪狼同宫：能量外放+欲望驱动，魅力极强，方向感需刻意建立",
                frozenset(["武曲","巨门"]): "武曲·巨门同宫：口才财气并重，适合谈判/销售/财务，言辞锋利需注意分寸",
                frozenset(["紫微","贪狼"]): "紫微·贪狼同宫：格局大、欲望强，成就感极强，需警惕被欲望驱动而非价值驱动",
                frozenset(["天机","太阴"]): "天机·太阴同宫：细腻智慧型，直觉准、分析强，易过度内耗",
                frozenset(["天同","天梁"]): "天同·天梁同宫：慈悲平和，贵人缘极佳，但主动性弱，需推一把才动",
            }
            pair_key = frozenset(main[:2])
            if pair_key in pair_notes:
                combo_note = f'<div class="prc-pair-note">「{pair_notes[pair_key]}」</div>'

        combo_html = "".join(combo_blocks)
        # 如果没有精确匹配，fallback 到原 reading
        if not combo_html and reading:
            combo_html = f'<p class="prc-reading-fallback">{reading}</p>'

        question_html = f'<div class="prc-question">{question}</div>' if question else ''
        return (
            f'<div class="palace-reading-card">'
            f'<div class="prc-header">'
            f'<span class="prc-icon">{icon}</span>'
            f'<div class="prc-title-block">'
            f'<span class="prc-name">{pname}</span>'
            f'<span class="prc-sub">{sub} · {zhi_c}宫</span>'
            f'</div>'
            f'<div class="prc-stars">{stars_html}{sihua_tags_html}</div>'
            f'</div>'
            + question_html
            + combo_note
            + f'<div class="prc-combos">{combo_html}</div>'
            + '</div>'
        )

    six_readings_html = "\n".join(render_prc(p) for p in SIX_PALACES)

    # ── 信息栏 ────────────────────────────────────────────────
    body_short = body_palace.split("，")[0] if "，" in body_palace else body_palace
    info_bar = (
        f'<div class="ziwei-info-bar">'
        f'<div class="zib-item"><span class="zib-label">命宫</span><span class="zib-val">{life_palace}</span></div>'
        f'<div class="zib-item"><span class="zib-label">身宫</span><span class="zib-val">{body_short}</span></div>'
        f'<div class="zib-item"><span class="zib-label">五行局</span><span class="zib-val">{wuxing_ju}</span></div>'
        f'<div class="zib-item"><span class="zib-label">命主</span><span class="zib-val">{life_master}</span></div>'
        f'<div class="zib-item"><span class="zib-label">身主</span><span class="zib-val">{body_master}</span></div>'
        f'<div class="zib-item"><span class="zib-label">大运方向</span><span class="zib-val">{dayun_dir}</span></div>'
        f'</div>'
    )

    overall_html = ""
    if pattern or overall:
        overall_html = (
            f'<div class="ziwei-overall">'
            f'<div class="ziwei-pattern-text">{pattern}</div>'
            f'<p class="ziwei-overall-text">{overall}</p>'
            f'</div>'
        )

    legend = (
        '<div class="ziwei-legend">'
        '<span class="legend-item"><span class="cell-marker marker-life" style="position:static;font-size:10px;padding:1px 4px;border-radius:3px">命</span> 命宫</span>'
        '<span class="legend-item"><span class="cell-marker marker-body" style="position:static;font-size:10px;padding:1px 4px;border-radius:3px">身</span> 身宫</span>'
        '<span class="legend-item"><span class="cell-marker marker-dayun" style="position:static;font-size:10px;padding:1px 4px;border-radius:3px">限</span> 当前大限</span>'
        '<span class="legend-item"><span class="ziwei-sihua-tag" style="background:#c9973a;position:static">禄</span> 化禄</span>'
        '<span class="legend-item"><span class="ziwei-sihua-tag" style="background:#c0392b;position:static">权</span> 化权</span>'
        '<span class="legend-item"><span class="ziwei-sihua-tag" style="background:#2980b9;position:static">科</span> 化科</span>'
        '<span class="legend-item"><span class="ziwei-sihua-tag" style="background:#7f8c8d;position:static">忌</span> 化忌</span>'
        '</div>'
    )

    return (
        f'<section class="report-section" id="ziwei">'
        f'<h2 class="section-title">紫微斗数</h2>'
        f'{info_bar}'
        f'<h3 class="ziwei-sub-title">十二宫星曜</h3>'
        f'<div class="ziwei-grid">{grid_cells}</div>'
        f'{legend}'
        f'{empty_panel_html}'
        f'<h3 class="ziwei-sub-title">四化飞星</h3>'
        f'<div class="sihua-cards">{sihua_cards_html}</div>'
        f'<h3 class="ziwei-sub-title">大限时间轴（{dayun_dir}）</h3>'
        f'{timeline_html}'
        f'{curr_dayun_detail}'
        f'<h3 class="ziwei-sub-title">六宫深度解读</h3>'
        f'<div class="palace-readings-grid">{six_readings_html}</div>'
        f'<h3 class="ziwei-sub-title">命盘整体格局</h3>'
        f'{overall_html}'
        f'</section>'
    )



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

    # ── 字段兼容层：统一 strokes_breakdown / five_grids / overall_rating ──
    # strokes：list[{字, 康熙笔画}] → strokes_breakdown dict
    if "strokes_breakdown" not in na and "strokes" in na:
        na = dict(na)
        na["strokes_breakdown"] = {item["字"]: item["康熙笔画"] for item in na["strokes"] if isinstance(item, dict)}

    # five_grids → wuge_scores（键名映射：天格→tianGe 等）
    if "wuge_scores" not in na and "five_grids" in na:
        na = dict(na)
        key_map = {"天格": "tianGe", "人格": "renGe", "地格": "diGe", "外格": "waiGe", "总格": "zongGe"}
        wuge_scores = {}
        for cn, en in key_map.items():
            g = na["five_grids"].get(cn, {})
            wuge_scores[en] = {
                "value": g.get("数理", ""),
                "name": g.get("名称", ""),
                "rating": g.get("吉凶", ""),
                "element": g.get("五行", ""),
                "meaning": g.get("含义", ""),
            }
        na["wuge_scores"] = wuge_scores

    # sancai：配置/评级/详细 → config/rating/detail
    sancai_raw = na.get("sancai", {})
    if isinstance(sancai_raw, dict) and "config" not in sancai_raw:
        sc = dict(sancai_raw)
        sc.setdefault("config", sancai_raw.get("配置", ""))
        sc.setdefault("rating", sancai_raw.get("分析", {}).get("评级", ""))
        detail_list = sancai_raw.get("分析", {}).get("详细", [])
        sc.setdefault("detail", "；".join(detail_list) if isinstance(detail_list, list) else str(detail_list))
        na = dict(na)
        na["sancai"] = sc

    # overall_rating
    if "overall_rating" not in na:
        na = dict(na)
        na["overall_rating"] = na.get("overall_grade", "")

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


def render_sixdim_section(person: dict, pid: str = "") -> str:
    """六维度评分 + 权重滑块 + JS 实时重算引擎
    pid: person id prefix，合盘多人时传入如 'p1_' / 'p2_' 避免 ID 冲突
    """
    import json as _json
    dims = person.get("six_dimensions")
    if not dims:
        return ""

    # pid 前缀：所有 DOM id 和 JS 函数名均含此前缀，防止合盘多人时 ID 冲突
    p = pid  # 如 "p1_" 或 ""

    DIM_META = [
        ("career",   "事业", "📐"),
        ("wealth",   "财运", "💰"),
        ("marriage", "婚姻", "❤"),
        ("health",   "健康", "🌿"),
        ("children", "子女", "🌱"),
        ("spirit",   "精神", "✦"),
    ]
    MODULE_ORDER = ["bazi", "ziwei", "bone", "western", "name", "mbti"]
    MODULE_CN    = {"bazi":"八字", "ziwei":"紫微", "bone":"称骨",
                    "western":"星座", "name":"姓名", "mbti":"MBTI"}

    # 把完整数据序列化进 HTML 供 JS 消费（键名带 pid 前缀）
    js_data = {}
    for key, cn, _ in DIM_META:
        d    = dims.get(key, {})
        sigs = d.get("signals", {})
        wts  = d.get("weights", {})
        pkey = f"{p}{key}"
        js_data[pkey] = {
            "cn":      cn,
            "label":   d.get("label", ""),
            "comment": d.get("comment", ""),
            "signals": {m: sigs[m]["score"] for m in MODULE_ORDER if m in sigs},
            "bases":   {m: sigs[m].get("basis", "") for m in MODULE_ORDER if m in sigs},
            "weights": {m: wts[m]["default"] for m in MODULE_ORDER if m in wts},
        }
    js_data_str = _json.dumps(js_data, ensure_ascii=False)

    # JS 函数名加前缀，避免合盘多人时互相覆盖
    fn_recalc = f"sdRecalc_{p.rstrip('_')}" if p else "sdRecalc"
    fn_reset  = f"sdReset_{p.rstrip('_')}"  if p else "sdReset"

    # 静态卡片骨架（JS 初始化后填充数值）
    cards_html = ""
    for key, cn, icon in DIM_META:
        d       = dims.get(key, {})
        comment = d.get("comment", "")
        sigs    = d.get("signals", {})
        wts     = d.get("weights", {})
        pkey    = f"{p}{key}"
        sig_rows = ""
        for m in MODULE_ORDER:
            if m not in sigs:
                continue
            sig_score = sigs[m]["score"]
            sig_basis = sigs[m].get("basis", "")
            default_w = wts.get(m, {}).get("default", 10)
            sig_rows += (
                f'<div class="sd-sig-row">'
                f'<div class="sd-sig-top">'
                f'<span class="sd-mod-name">{MODULE_CN[m]}</span>'
                f'<span class="sd-sig-score">{sig_score}</span>'
                f'<div class="sd-slider-wrap">'
                f'<input type="range" class="sd-weight-slider"'
                f' data-dim="{pkey}" data-mod="{m}"'
                f' min="0" max="50" step="1" value="{default_w}"'
                f' oninput="{fn_recalc}(\'{pkey}\')" />'
                f'<span class="sd-weight-val" id="sdw-{pkey}-{m}">{default_w}</span>'
                f'</div></div>'
                f'<div class="sd-basis">{sig_basis}</div>'
                f'</div>'
            )
        cards_html += (
            f'<div class="sixdim-card" id="sdcard-{pkey}">'
            f'<div class="sd-card-header">'
            f'<span class="sd-icon">{icon}</span>'
            f'<span class="sd-cn">{cn}</span>'
            f'<div class="sd-score-pill">'
            f'<span class="sd-score-num" id="sdscore-{pkey}">—</span>'
            f'<span class="sd-score-max">/100</span>'
            f'</div></div>'
            f'<div class="sd-bar-wrap"><div class="sd-bar" id="sdbar-{pkey}"></div></div>'
            f'<div class="sd-label" id="sdlabel-{pkey}"></div>'
            f'<div class="sd-comment">{comment}</div>'
            f'<details class="sd-detail">'
            f'<summary class="sd-detail-toggle">权重调整 · 信号来源</summary>'
            f'<div class="sd-sig-list">'
            f'<div class="sd-sig-header"><span>模块</span><span>信号分</span><span>权重（拖动调整）</span></div>'
            f'{sig_rows}'
            f'<button class="sd-reset-btn" onclick="{fn_reset}(\'{pkey}\')">恢复默认权重</button>'
            f'</div></details>'
            f'</div>'
        )

    js_engine = (
        f"<script>\n(function(){{\n"
        f"  var SD_DATA = {js_data_str};\n"
        "\n"
        "  function scoreToColor(pct) {\n"
        "    if (pct >= 0.8) return '#c9973a';\n"
        "    if (pct >= 0.6) return '#4a7c59';\n"
        "    if (pct >= 0.4) return '#7a6a55';\n"
        "    return '#b5451b';\n"
        "  }\n"
        "\n"
        f"  window.{fn_recalc} = function(dimKey) {{\n"
        "    var d = SD_DATA[dimKey];\n"
        "    if (!d) return;\n"
        "    var sliders = document.querySelectorAll('.sd-weight-slider[data-dim=\\'' + dimKey + '\\']');\n"
        "    var wsum = 0, score = 0;\n"
        "    sliders.forEach(function(sl) {\n"
        "      var mod = sl.dataset.mod;\n"
        "      var w   = parseFloat(sl.value);\n"
        "      var s   = d.signals[mod] || 0;\n"
        "      wsum  += w;\n"
        "      score += s * w;\n"
        "      var wlabel = document.getElementById('sdw-' + dimKey + '-' + mod);\n"
        "      if (wlabel) wlabel.textContent = w;\n"
        "    });\n"
        "    var final = wsum > 0 ? score / wsum : 0;\n"
        "    var pct   = Math.min(final / 100, 1);\n"
        "    var color = scoreToColor(pct);\n"
        "    var numEl   = document.getElementById('sdscore-'  + dimKey);\n"
        "    var barEl   = document.getElementById('sdbar-'    + dimKey);\n"
        "    var labelEl = document.getElementById('sdlabel-'  + dimKey);\n"
        "    var cardEl  = document.getElementById('sdcard-'   + dimKey);\n"
        "    if (numEl)   numEl.textContent  = final.toFixed(1);\n"
        "    if (barEl)   { barEl.style.width = (pct*100).toFixed(1)+'%'; barEl.style.background = color; }\n"
        "    if (labelEl) { labelEl.textContent = d.label; labelEl.style.color = color; }\n"
        "    if (cardEl)  cardEl.style.setProperty('--dim-color', color);\n"
        "  };\n"
        "\n"
        f"  window.{fn_reset} = function(dimKey) {{\n"
        "    var d = SD_DATA[dimKey];\n"
        "    if (!d) return;\n"
        "    var sliders = document.querySelectorAll('.sd-weight-slider[data-dim=\\'' + dimKey + '\\']');\n"
        "    sliders.forEach(function(sl) {\n"
        "      var mod = sl.dataset.mod;\n"
        "      if (d.weights[mod] !== undefined) sl.value = d.weights[mod];\n"
        "    });\n"
        f"    {fn_recalc}(dimKey);\n"
        "  };\n"
        "\n"
        "  var dims = Object.keys(SD_DATA);\n"
        f"  dims.forEach(function(dk) {{ {fn_recalc}(dk); }});\n"
        "})();\n"
        "</script>"
    )

    return (
        '\n    <section class="report-section" id="sixdim">'
        '\n      <h2 class="section-title">六维度评分</h2>'
        '\n      <p class="sd-intro">综合八字、紫微、称骨、星座、姓名、MBTI六大模块加权合成。'
        '展开每个维度可查看各模块信号分并自由调整权重，分数实时更新。</p>'
        f'\n      <div class="sixdim-grid">{cards_html}</div>'
        '\n    </section>'
        f'\n    {js_engine}'
    )

def render_sketch_section(person: dict) -> str:
    sk = person.get("personality_sketch", {})
    inner = sk.get("inner_core", "")
    destiny = sk.get("destiny_direction", "")
    outer = sk.get("outer_expression", "")
    reconciliation = sk.get("reconciliation_theme", "") or sk.get("reconciliation", "")
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
    if not notes:
        return ""
    return (
        f'<section class="report-section" id="confidence">'
        f'<h2 class="section-title">置信度说明</h2>'
        f'<p class="conf-notes">{notes}</p>'
        f'</section>'
    )


def render_person_full(person: dict, pid: str = "") -> str:
    """渲染单人完整命盘所有 section
    pid: 传给 render_sixdim_section 用于 ID 前缀隔离（合盘多人时必须传入）
    """
    return "".join([
        render_hero(person),
        render_bazi_section(person),
        render_bone_section(person),
        render_ziwei_section(person),
        render_western_section(person),
        render_name_section(person),
        render_sixdim_section(person, pid=pid),
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
      <button class="full-detail-btn" onclick="(function(){{
        var target = document.getElementById('full-person-{idx}');
        if(target){{
          target.open = true;
          target.scrollIntoView({{behavior:'smooth', block:'start'}});
        }}
      }})()" title="跳转至完整命盘">展开完整命盘 ↓</button>
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



import json as _json

def render_relation_matrix(persons: list, synastry: dict) -> str:
    """
    渲染关系矩阵图（适用于双人/多人合盘）。
    双视图：① 上三角热力矩阵表（快速总览）② 力导向关系网络图（D3.js）
    数据来源：synastry.relation_matrix 列表，每项含 a, b, total, sx_rel, rz_rel, type, note。
    若 relation_matrix 不存在则自动从 shengxiao_matrix 推导基础版。
    """
    if not persons or len(persons) < 2:
        return ""

    names = [p.get("name", "") for p in persons]
    n = len(names)

    # ── 获取或推导关系对列表 ────────────────────────────────────────────────
    pairs_raw = synastry.get("relation_matrix", [])
    if not pairs_raw:
        good = synastry.get("shengxiao_matrix", {}).get("good", [])
        tension = synastry.get("shengxiao_matrix", {}).get("tension", [])
        pair_map = {}
        for g in good:
            raw_pair = g.get("pair", "")
            score_str = str(g.get("score", "+3")).strip()
            try:
                score = int(score_str.lstrip("+"))
            except ValueError:
                score = 3
            a, b = _extract_pair_names(raw_pair, names)
            if a and b:
                ptype = "strong_pull" if score >= 9 else ("pull" if score >= 6 else "neutral")
                pair_map[(a, b)] = {"a": a, "b": b, "total": score, "sx_rel": g.get("relation", ""), "rz_rel": "", "note": g.get("note", ""), "type": ptype}
        for t in tension:
            raw_pair = t.get("pair", "")
            score_str = str(t.get("score", "-2")).strip()
            try:
                score = int(score_str)
            except ValueError:
                score = -2
            a, b = _extract_pair_names(raw_pair, names)
            if a and b:
                ptype = "strong_tension" if score <= -5 else ("tension" if score <= -3 else "mild_tension")
                pair_map[(a, b)] = {"a": a, "b": b, "total": score, "sx_rel": t.get("relation", ""), "rz_rel": "", "note": t.get("note", ""), "type": ptype}
        for i in range(n):
            for j in range(i + 1, n):
                key = (names[i], names[j])
                rkey = (names[j], names[i])
                if key not in pair_map and rkey not in pair_map:
                    pair_map[key] = {"a": names[i], "b": names[j], "total": 3, "sx_rel": "平和", "rz_rel": "", "note": "", "type": "neutral"}
        pairs_raw = list(pair_map.values())

    # ── 建立查找字典 ─────────────────────────────────────────────────────────
    pair_dict = {}
    for p in pairs_raw:
        key = (p.get("a", ""), p.get("b", ""))
        pair_dict[key] = p
        pair_dict[(key[1], key[0])] = p

    TYPE_META = {
        "strong_pull":    {"color": "#2d7a4f", "bg": "#d4f0e2", "label": "强引力",   "dot": "◉"},
        "pull":           {"color": "#3d7a5a", "bg": "#e8f5ee", "label": "引力",     "dot": "◎"},
        "neutral":        {"color": "#8b6820", "bg": "#f5f0e0", "label": "平和",     "dot": "○"},
        "mild_tension":   {"color": "#a05820", "bg": "#fdf0e0", "label": "轻度张力", "dot": "◈"},
        "tension":        {"color": "#9b3020", "bg": "#fde8e4", "label": "张力",     "dot": "◆"},
        "strong_tension": {"color": "#7b1810", "bg": "#fad0ca", "label": "强张力",   "dot": "◆◆"},
    }

    def get_pair(a, b):
        return pair_dict.get((a, b)) or pair_dict.get((b, a))

    def get_type(a, b):
        p = get_pair(a, b)
        return p.get("type", "neutral") if p else "neutral"

    def get_total(a, b):
        p = get_pair(a, b)
        return p.get("total", 3) if p else 3

    def get_rel_label(a, b):
        p = get_pair(a, b)
        if not p:
            return "平和"
        parts = [x for x in [p.get("sx_rel", ""), p.get("rz_rel", "")] if x]
        return "·".join(parts[:2]) if parts else "平和"

    def get_note(a, b):
        p = get_pair(a, b)
        return p.get("note", "") if p else ""

    # ── ① 全对称矩阵表（上下三角均填充，对角线为自身标识）────────────────────────
    col_label = lambda nm: nm  # 始终使用全名，不简写
    header_cells = "".join(
        f'<th class="matrix-col-head" title="{nm}">{col_label(nm)}</th>' for nm in names
    )
    rows_html = ""
    for i, row_name in enumerate(names):
        cells = f'<th class="matrix-row-head">{row_name}</th>'
        for j, col_name in enumerate(names):
            if j == i:
                cells += f'<td class="matrix-cell matrix-cell-self"><span class="matrix-self-dot" style="color:#4a3a28;font-size:.72rem">{row_name}</span></td>'
            else:
                ptype = get_type(row_name, col_name)
                total = get_total(row_name, col_name)
                rel = get_rel_label(row_name, col_name)
                note = get_note(row_name, col_name)
                meta = TYPE_META.get(ptype, TYPE_META["neutral"])
                sign = "+" if total >= 0 else ""
                tooltip_parts = [f"{row_name}×{col_name}", rel]
                if note:
                    tooltip_parts.append(note)
                tooltip = "\n".join(tooltip_parts)
                cells += (
                    f'<td class="matrix-cell matrix-cell-data" '
                    f'style="background:{meta["bg"]};" '
                    f'data-a="{row_name}" data-b="{col_name}" '
                    f'title="{tooltip}">'
                    f'<span class="matrix-dot" style="color:{meta["color"]};">{meta["dot"]}</span>'
                    f'<span class="matrix-score" style="color:{meta["color"]};">{sign}{total}</span>'
                    f'</td>'
                )
        rows_html += f"<tr>{cells}</tr>\n"

    legend_html = "".join(
        f'<span class="matrix-legend-item"><span style="color:{m["color"]};">{m["dot"]}</span> {m["label"]}</span>'
        for m in TYPE_META.values()
    )


    uid = f"rm{abs(hash(str(names))) % 100000}"

    return f"""
    <section class="report-section" id="relation-matrix-{uid}">
      <h2 class="section-title">关系矩阵图</h2>

      <div class="matrix-legend">{legend_html}</div>

      <div class="matrix-table-wrap">
        <table class="matrix-table" id="mtable-{uid}">
          <thead><tr><th class="matrix-corner"></th>{header_cells}</tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>

      <div class="matrix-tooltip" id="mtooltip-{uid}"></div>


    </section>

    <style>
    .matrix-legend{{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:14px;font-size:.78rem}}
    .matrix-legend-item{{display:flex;align-items:center;gap:4px;color:var(--color-ink-secondary,#6b5a47)}}
    .matrix-table-wrap{{overflow-x:auto;margin-bottom:20px}}
    .matrix-table{{border-collapse:collapse;width:100%}}
    .matrix-table th,.matrix-table td{{border:1px solid var(--color-border,#e4d5bc)}}
    .matrix-corner{{background:var(--color-bg-page,#faf7f2);width:28px;min-width:28px}}
    .matrix-col-head{{background:#1a1410;color:#e8c47a;font-size:.78rem;padding:6px 8px;text-align:center;min-width:64px}}
    .matrix-row-head{{background:#1a1410;color:#e8c47a;font-size:.78rem;padding:6px 10px;text-align:right;white-space:nowrap}}
    .matrix-cell{{text-align:center;cursor:default;transition:filter .15s;padding:0}}
    .matrix-cell:hover{{filter:brightness(.88);cursor:pointer}}
    .matrix-cell-empty{{background:var(--color-bg-page,#faf7f2)}}
    .matrix-cell-self{{background:#1a1410;vertical-align:middle;text-align:center}}
    .matrix-self-dot{{color:#3a2810;font-size:1em}}
    .matrix-cell-data{{padding:6px 4px}}
    .matrix-dot{{display:block;font-size:1em;line-height:1.2}}
    .matrix-score{{display:block;font-size:.7rem;font-weight:700}}
    .matrix-tooltip{{position:fixed;background:#1a1410;color:#e8c47a;padding:8px 12px;border-radius:4px;font-size:.78rem;line-height:1.7;pointer-events:none;opacity:0;transition:opacity .15s;max-width:220px;z-index:9999;border:1px solid #4a3a20;white-space:pre-line}}
    </style>

    <script>
    (function(){{
      var tip = document.getElementById('mtooltip-{uid}');
      document.querySelectorAll('#mtable-{uid} .matrix-cell-data').forEach(function(cell){{
        cell.addEventListener('mouseenter', function(e){{
          tip.textContent = cell.getAttribute('title') || '';
          tip.style.opacity = '1';
          tip.style.left = (e.clientX + 14) + 'px';
          tip.style.top  = (e.clientY - 8)  + 'px';
        }});
        cell.addEventListener('mousemove', function(e){{
          tip.style.left = (e.clientX + 14) + 'px';
          tip.style.top  = (e.clientY - 8)  + 'px';
        }});
        cell.addEventListener('mouseleave', function(){{
          tip.style.opacity = '0';
        }});
      }});
    }})();
    </script>"""


def _extract_pair_names(raw_pair: str, names: list):
    """从 '郭律均(戌)×娄江溶(卯)' 格式中提取两个姓名"""
    found = [nm for nm in names if nm in raw_pair]
    return (found[0], found[1]) if len(found) >= 2 else (None, None)


def render_communication_guide(synastry: dict) -> str:
    """渲染关系指南 section（沟通要点 + 关系发展建议）"""
    guide = synastry.get("communication_guide", {})
    advices = synastry.get("scenario_advice", [])
    if not guide and not advices:
        return ""

    p1_name = synastry.get("_p1_name", "她")
    p2_name = synastry.get("_p2_name", "他")

    # 沟通要点卡片
    friction_html = f'<p class="guide-friction">{guide.get("key_friction","")}</p>' if guide.get("key_friction") else ""

    def list_to_html(items):
        return "".join(f'<li>{item}</li>' for item in items) if items else ""

    her_items = list_to_html(guide.get("her_to_him", []))
    him_items = list_to_html(guide.get("him_to_her", []))
    window_html = f'<p class="guide-window">⏳ {guide.get("window","")}</p>' if guide.get("window") else ""
    reconcile = guide.get("reconciliation", "")

    guide_html = ""
    if guide:
        guide_html = f"""
    <section class="report-section" id="communication-guide">
      <h2 class="section-title">关系指南</h2>
      {friction_html}
      <div class="guide-cols">
        {"" if not her_items else f'<div class="guide-col"><h4>{p1_name} → {p2_name}</h4><ul>{her_items}</ul></div>'}
        {"" if not him_items else f'<div class="guide-col"><h4>{p2_name} → {p1_name}</h4><ul>{him_items}</ul></div>'}
      </div>
      {window_html}
      {"" if not reconcile else f'<blockquote class="guide-reconcile">「{reconcile}」</blockquote>'}
    </section>"""

    # 场景建议 Tab（从 scenario_advice 渲染，替代原来空的 render_scenario_tabs）
    scenario_html = ""
    if advices:
        tabs_h = ""
        panels_h = ""
        for i, item in enumerate(advices):
            sc = item.get("scenario", "")
            adv = item.get("advice", "").replace("\n\n", "</p><p>").replace("\n", "<br>")
            active = ' class="scenario-tab active"' if i == 0 else ' class="scenario-tab"'
            hidden = "" if i == 0 else " hidden"
            tabs_h += f'<button{active} data-target="scenario-adv-{i}">{sc}</button>'
            panels_h += f'<div class="scenario-content" id="scenario-adv-{i}"{hidden}><p>{adv}</p></div>'
        scenario_html = f"""
    <section class="report-section" id="scenarios">
      <h2 class="section-title">场景化建议</h2>
      <div class="scenario-tabs">{tabs_h}</div>
      <div class="scenario-panels">{panels_h}</div>
    </section>"""

    return guide_html + scenario_html


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
    synastry["_p1_name"] = p1_name
    synastry["_p2_name"] = p2_name
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
    scenarios_html = render_communication_guide(synastry)

    # 底部折叠完整命盘
    full_html = ""
    for p_idx, p in enumerate(persons, start=1):
        pname = p.get("name", f"命主{p.get('person_index', p_idx)}")
        person_pid = f"p{p_idx}_"
        full_html += f"""
        <details class="full-person-details" id="full-person-{p.get('person_index', p_idx)}">
          <summary class="full-person-summary">▶ {pname} 完整命盘</summary>
          <div class="full-person-inner">{render_person_full(p, pid=person_pid)}</div>
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

/* ======= 紫微斗数细致排盘 CSS ======= */
.ziwei-info-bar{display:flex;flex-wrap:wrap;gap:8px 18px;background:#faf3e6;border:1px solid #e8d9b8;border-radius:8px;padding:12px 16px;margin-bottom:20px}
.zib-item{display:flex;align-items:center;gap:6px}
.zib-label{font-size:11px;color:#888;font-weight:600;letter-spacing:.5px}
.zib-val{font-size:13px;color:#1a1410;font-weight:700}

.ziwei-sub-title{font-size:14px;font-weight:700;color:var(--color-gold);letter-spacing:1.5px;margin:22px 0 10px;padding-bottom:4px;border-bottom:1px solid #e8d9b8;text-transform:none}

/* 十二宫网格 */
.ziwei-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:8px}
.ziwei-cell{background:#fff;border:1px solid #e0d4bf;border-radius:6px;padding:8px 10px;min-height:80px;position:relative;transition:box-shadow .15s}
.ziwei-cell:hover{box-shadow:0 2px 8px rgba(201,151,58,.2)}
.cell-life{border-color:var(--color-gold);background:#fffbf0}
.cell-body{border-color:#8e6bbf;background:#faf7ff}
.cell-curr-dayun{border-color:#e74c3c;background:#fff8f8}
.cell-has-reading{box-shadow:inset 2px 0 0 var(--color-gold)}
.cell-header{display:flex;align-items:center;gap:5px;margin-bottom:6px;flex-wrap:wrap}
.cell-zhi{font-size:18px;font-weight:800;color:var(--color-gold);line-height:1}
.cell-name{font-size:10px;color:#777;font-weight:600;letter-spacing:.5px}
.cell-marker{position:absolute;top:5px;right:5px;font-size:9px;font-weight:800;padding:1px 4px;border-radius:3px;line-height:1.4}
.marker-life{background:var(--color-gold);color:#fff}
.marker-body{background:#8e6bbf;color:#fff}
.marker-dayun{background:#e74c3c;color:#fff}
.cell-main-stars{display:flex;flex-wrap:wrap;gap:3px;margin-bottom:4px}
.cell-aux-stars{display:flex;flex-wrap:wrap;gap:2px}
.ziwei-star-badge{display:inline-flex;align-items:center;gap:2px;background:#faf3e6;border:1px solid #d4b896;color:#5c3d0e;font-size:11px;font-weight:700;padding:2px 6px;border-radius:4px}
.ziwei-star-badge-sm{display:inline-flex;align-items:center;gap:1px;background:#f5f5f5;border:1px solid #ddd;color:#666;font-size:9px;padding:1px 4px;border-radius:3px}
.ziwei-sihua-tag{display:inline-block;color:#fff;font-size:9px;font-weight:800;padding:0px 3px;border-radius:2px;margin-left:1px;position:relative;top:-1px}
.ziwei-empty-cell{font-size:10px;color:#bbb;font-style:italic}
.ziwei-legend{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:11px;color:#777;margin-bottom:16px;padding:8px 12px;background:#fafafa;border-radius:6px}
.legend-item{display:flex;align-items:center;gap:4px}

/* 四化卡片 */
.sihua-cards{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:4px}
@media(max-width:600px){.sihua-cards{grid-template-columns:1fr}}
.sihua-card{background:#fff;border-radius:8px;padding:12px 14px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.sihua-card-header{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px}
.sihua-badge{color:#fff;font-size:14px;font-weight:800;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0}
.sihua-tag-name{font-size:13px;font-weight:700}
.sihua-star{font-size:12px;color:#555}
.sihua-palace{font-size:11px;color:#888;margin-left:auto}
.sihua-meaning{font-size:11px;font-weight:600;color:#777;margin-bottom:4px}
.sihua-desc{font-size:12px;color:#555;margin-bottom:6px}
.sihua-palace-snippet{font-size:11px;color:#888;background:#f8f6f2;border-radius:4px;padding:5px 8px;line-height:1.5;border-left:2px solid #e0d4bf}

/* 大限时间轴 */
.dayun-timeline{display:flex;flex-direction:column;gap:0;margin-bottom:16px;padding:8px 0}
.dayun-item{display:grid;grid-template-columns:100px 16px 1fr;align-items:center;gap:0 12px;padding:6px 0;border-bottom:1px solid #f0ebe0;font-size:12px}
.dayun-item:last-child{border-bottom:none}
.dayun-curr{background:#fffcf4;border-radius:6px;padding:8px 10px}
.dayun-rng{color:#555;font-weight:600;font-size:11px;display:flex;align-items:center;gap:6px;white-space:nowrap}
.dayun-curr-tag{background:#c9973a;color:#fff;font-size:9px;font-weight:800;padding:1px 5px;border-radius:3px}
.dayun-dot{width:8px;height:8px;border-radius:50%;background:#d4b896;flex-shrink:0;justify-self:center}
.dayun-curr .dayun-dot{background:#c9973a;width:10px;height:10px}
.dayun-info{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.dayun-palace-nm{font-weight:700;color:#3a2a10}
.dayun-zhi-nm{color:#888;font-size:11px}
.dayun-stars-nm{color:var(--color-gold);font-size:11px;font-weight:600}
.curr-dayun-detail{background:#fffbf0;border:1px solid #e8d9b8;border-radius:8px;padding:14px 16px;margin-bottom:16px}
.curr-dayun-label{font-size:11px;font-weight:700;color:var(--color-gold);letter-spacing:.5px;margin-bottom:8px}
.curr-dayun-text{font-size:13px;color:#3a2a10;line-height:1.8;margin:0}

/* 六宫深度解读 */
.palace-readings-grid{display:flex;flex-direction:column;gap:12px;margin-bottom:8px}
.palace-reading-card{background:#fff;border:1px solid #e0d4bf;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.prc-header{display:flex;align-items:flex-start;gap:12px;margin-bottom:10px;flex-wrap:wrap}
.prc-icon{font-size:20px;flex-shrink:0;line-height:1.2}
.prc-title-block{display:flex;flex-direction:column;gap:2px;min-width:100px}
.prc-name{font-size:15px;font-weight:800;color:#1a1410}
.prc-sub{font-size:10px;color:#999;letter-spacing:.5px}
.prc-stars{display:flex;flex-wrap:wrap;gap:4px;align-items:center;margin-left:auto}
.prc-reading{font-size:13px;color:#3a2a10;line-height:1.85;margin:0}

/* 整体格局 */
.ziwei-overall{background:#faf3e6;border-radius:8px;padding:14px 16px;border:1px solid #e8d9b8}
.ziwei-pattern-text{font-size:13px;font-weight:700;color:#3a2a10;margin-bottom:8px;line-height:1.7}
.ziwei-overall-text{font-size:13px;color:#555;line-height:1.85;margin:0}

/* ── 空宫对宫提示 ── */
.cell-empty{border-style:dashed;border-color:#d4c9b4;background:#fafaf7}
.borrow-hint{display:block;font-size:9px;color:#9e7c3a;font-style:italic;margin-top:3px;line-height:1.4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* ── 空宫对宫面板 ── */
.empty-palace-panel{background:#faf8f3;border:1px solid #e0d4bf;border-radius:8px;padding:12px 14px;margin:8px 0 16px}
.ep-panel-title{font-size:11px;font-weight:700;color:var(--color-gold);letter-spacing:.8px;margin-bottom:10px}
.empty-palace-item{padding:7px 0;border-bottom:1px solid #ede6d6;display:flex;flex-direction:column;gap:3px}
.empty-palace-item:last-child{border-bottom:none}
.ep-header{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.ep-name{font-size:12px;font-weight:700;color:#3a2a10;min-width:52px}
.ep-arrow{font-size:11px;color:#bbb}
.ep-opp{font-size:12px;color:#555;font-weight:600}
.ep-stars{font-size:12px;color:var(--color-gold);font-weight:700;margin-left:4px}
.ep-desc{font-size:11px;color:#777;line-height:1.6;padding-left:2px}
.ep-reading{font-size:10px;color:#999;background:#f5f0e8;border-radius:3px;padding:3px 7px;line-height:1.5;margin-top:2px}


/* 旧样式兜底 */
.ziwei-header{display:none}
.dayun-card{display:none}
.ziwei-analysis{display:none}
/* ======= 紫微斗数细致排盘 CSS END ======= */


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
/* ── 六维度评分 ── */
.sd-intro { font-size: .82rem; color: var(--color-ink-muted); margin-bottom: 14px; line-height: 1.7; }
.sixdim-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 16px; }
@media (max-width: 640px) { .sixdim-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 400px) { .sixdim-grid { grid-template-columns: 1fr; } }

.sixdim-card {
  --dim-color: #7a6a55;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-top: 3px solid var(--dim-color);
  border-radius: var(--radius);
  padding: 14px;
  transition: border-top-color .3s;
}
.sd-card-header { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.sd-icon   { font-size: 1rem; }
.sd-cn     { font-size: .9rem; font-weight: 600; color: var(--color-ink); flex: 1; }
.sd-score-pill { display: flex; align-items: baseline; gap: 1px; }
.sd-score-num  { font-size: 1.5rem; font-weight: 700; color: var(--dim-color); transition: color .3s; }
.sd-score-max  { font-size: .72rem; color: var(--color-ink-muted); }

.sd-bar-wrap { height: 6px; background: var(--color-border); border-radius: 3px; overflow: hidden; margin-bottom: 6px; }
.sd-bar      { height: 100%; border-radius: 3px; width: 0%; transition: width .5s ease, background .3s; }
.sd-label    { font-size: .75rem; font-weight: 600; margin-bottom: 6px; transition: color .3s; }
.sd-comment  { font-size: .78rem; color: var(--color-ink-secondary); line-height: 1.75; margin-bottom: 8px; }

/* 展开区 */
.sd-detail { border-top: 1px solid var(--color-border); margin-top: 8px; padding-top: 8px; }
.sd-detail-toggle {
  font-size: .75rem; color: var(--color-ink-muted); cursor: pointer;
  list-style: none; user-select: none; padding: 2px 0;
}
.sd-detail-toggle::-webkit-details-marker { display: none; }
.sd-detail-toggle::before { content: '▶ '; font-size: .65rem; }
details[open] .sd-detail-toggle::before { content: '▼ '; }

.sd-sig-list { margin-top: 10px; }
.sd-sig-header {
  display: grid; grid-template-columns: 3rem 3rem 1fr;
  font-size: .68rem; color: var(--color-ink-muted);
  padding: 0 0 4px; border-bottom: 1px solid var(--color-border);
  margin-bottom: 6px; gap: 6px;
}
.sd-sig-row { margin-bottom: 10px; }
.sd-sig-top {
  display: grid; grid-template-columns: 3rem 3rem 1fr;
  align-items: center; gap: 6px;
}
.sd-mod-name  { font-size: .78rem; font-weight: 600; color: var(--color-ink); }
.sd-sig-score { font-size: .85rem; font-weight: 700; color: var(--color-gold); }
.sd-slider-wrap { display: flex; align-items: center; gap: 5px; }
.sd-weight-slider {
  flex: 1; height: 3px; cursor: pointer; accent-color: var(--color-gold);
  -webkit-appearance: none; appearance: none;
  background: var(--color-border); border-radius: 2px;
}
.sd-weight-slider::-webkit-slider-thumb {
  -webkit-appearance: none; width: 14px; height: 14px;
  border-radius: 50%; background: var(--color-gold); cursor: pointer;
  box-shadow: 0 1px 3px rgba(0,0,0,.2);
}
.sd-weight-val { font-size: .72rem; color: var(--color-ink-muted); min-width: 18px; text-align: right; }
.sd-basis { font-size: .72rem; color: var(--color-ink-muted); line-height: 1.6; margin-top: 3px;
  padding-left: 3rem; grid-column: 1/-1; }
.sd-reset-btn {
  margin-top: 8px; font-size: .72rem; padding: 4px 10px;
  border: 1px solid var(--color-border); border-radius: 4px;
  background: transparent; color: var(--color-ink-muted); cursor: pointer;
}
.sd-reset-btn:hover { border-color: var(--color-gold); color: var(--color-gold); }

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
.conf-notes { font-size: 13px; color: #555; line-height: 1.9; }
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
.full-detail-btn {
  display:inline-block; margin-top:10px; padding:4px 14px;
  background:transparent; border:1px solid var(--color-gold);
  color:var(--color-gold); border-radius:4px; font-size:.78rem;
  cursor:pointer; transition:background .2s,color .2s; font-family:inherit;
}
.full-detail-btn:hover { background:var(--color-gold); color:#fff8ee; }
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

/* ── 六宫深度解读动态层 ── */
.prc-question { font-size:.78rem; color:var(--color-ink-muted); font-style:italic;
  margin:.3rem 0 .6rem; padding-left:.5rem; border-left:2px solid var(--color-border); }
.prc-pair-note { font-size:.8rem; color:var(--color-ink-secondary); background:#f7f2ea;
  border-radius:4px; padding:.4rem .7rem; margin:.4rem 0; font-style:italic; }
.prc-combos { margin-top:.5rem; display:flex; flex-direction:column; gap:.5rem; }
.prc-combo { display:grid; grid-template-columns:3.5rem 1fr; gap:.4rem; align-items:start; }
.prc-combo-star { font-size:.78rem; font-weight:600; color:var(--color-gold);
  background:#fdf5e6; padding:.3rem .4rem; border-radius:4px; text-align:center; margin-top:.1rem; }
.prc-combo-content { display:flex; flex-direction:column; gap:.2rem; }
.prc-adv   { font-size:.8rem; color:#3d6b54; line-height:1.6; }
.prc-risk  { font-size:.8rem; color:#8b5e3c; line-height:1.6; }
.prc-action{ font-size:.8rem; color:var(--color-ink-secondary); line-height:1.6;
  font-style:italic; border-top:1px dashed var(--color-border); padding-top:.2rem; margin-top:.1rem; }
.prc-reading-fallback { font-size:.82rem; color:var(--color-ink-secondary); line-height:1.75; margin:0; }
.prc-sihua-tag { vertical-align:middle; }

/* ── 关系指南 ── */
.guide-friction { font-size:.85rem; color:var(--color-ink-secondary); background:var(--color-bg-card);
  border-left:3px solid var(--color-gold); padding:.6rem 1rem; border-radius:4px; margin-bottom:1rem; }
.guide-cols { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem; }
@media(max-width:600px){ .guide-cols { grid-template-columns:1fr; } }
.guide-col h4 { font-size:.85rem; color:var(--color-gold); margin-bottom:.5rem; }
.guide-col ul { margin:0; padding-left:1.2rem; }
.guide-col li { font-size:.83rem; color:var(--color-ink-secondary); line-height:1.7; margin-bottom:.3rem; }
.guide-window { font-size:.82rem; color:var(--color-ink-secondary); margin:.6rem 0;
  background:#f5f0e8; padding:.5rem .9rem; border-radius:4px; }
.guide-reconcile { border-left:3px solid var(--color-accent-jade); padding:.6rem 1.1rem;
  margin:1rem 0 0; font-style:italic; color:var(--color-ink-secondary); font-size:.88rem; }
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
