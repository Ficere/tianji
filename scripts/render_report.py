#!/usr/bin/env python3
"""天机固定报告格式：chart.json（事实）+ narrative.json（解读）→ Markdown + HTML。

事实字段（四柱、十神、藏干、纳音、五行、称骨、紫微宫位与四化、大限、星座度数、
五格数理、合盘分项）一律取自 chart.json；narrative.json 只承载 Agent 的解读文字。
两份输出内容一致：Markdown 是 HTML 的纯文本镜像。
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fortune_calc import _score_rizhu_pair, _score_shengxiao_pair  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NARRATIVE_SCHEMA = ROOT / "schemas" / "narrative_v1.schema.json"

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
WX_ORDER = ["木", "火", "土", "金", "水"]
MAJOR = ["紫微", "天机", "太阳", "武曲", "天同", "廉贞", "天府",
         "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"]
PALACES = ["命宫", "兄弟宫", "夫妻宫", "子女宫", "财帛宫", "疾厄宫",
           "迁移宫", "交友宫", "官禄宫", "田宅宫", "福德宫", "父母宫"]
OPPOSITE = {p: PALACES[(i + 6) % 12] for i, p in enumerate(PALACES)}
TIGER = {"甲": "丙", "己": "丙", "乙": "戊", "庚": "戊", "丙": "庚", "辛": "庚",
         "丁": "壬", "壬": "壬", "戊": "甲", "癸": "甲"}
DIMS = [("career", "事业"), ("wealth", "财运"), ("marriage", "婚姻"),
        ("health", "健康"), ("children", "子女"), ("spirit", "精神")]
SIGNAL_LABEL = {"bazi": "八字", "ziwei": "紫微", "bone": "称骨",
                "zodiac": "星座", "name": "姓名", "mbti": "MBTI"}
DEFAULT_WEIGHTS = {"bazi": 30, "ziwei": 30, "bone": 15, "zodiac": 10, "name": 5, "mbti": 10}
RECONCILE_RE = re.compile(r"与.+和解——不是.+，而是.+。")
DISCLAIMER = "命理分析属于民俗文化参考，不构成职业、医疗、法律、教育或投资建议。人生走向主要取决于个人选择与努力。"


class ReportError(ValueError):
    pass


# ---------------------------------------------------------------- facts

def palace_stems(year_gan: str) -> dict[str, str]:
    start = GAN.index(TIGER[year_gan])
    return {ZHI[(2 + k) % 12]: GAN[(start + k) % 10] for k in range(12)}


def facts(member: dict, as_of_year: int) -> dict:
    """把 chart.json 成员整理成渲染所需的事实视图（不做任何解释）。"""
    zw = member["ziwei"]
    stems = palace_stems(member["bazi"][0][0])
    sihua = {v["星曜"]: k[-1] for k, v in zw["四化飞星"].items()}
    grid = {}
    for palace in PALACES:
        zhi = zw["十二宫"][palace]
        stars = zw["十二宫星曜"].get(palace, [])
        grid[palace] = {
            "zhi": zhi, "gan": stems[zhi],
            "main": [s for s in stars if s in MAJOR],
            "aux": [s for s in stars if s not in MAJOR],
        }
    for palace, cell in grid.items():
        cell["borrow"] = grid[OPPOSITE[palace]]["main"] if not cell["main"] else []
    cang_ss = None
    deep = member.get("deep") or {}
    if deep.get("canggan_shishen"):
        cang_ss = [[c["十神"] for c in col["藏干"]] for col in deep["canggan_shishen"]["四柱藏干"]]
    birth_year = int(member["solar_date"][:4])
    xu_age = as_of_year - birth_year + 1
    current = None
    for d in zw["大限序列"]:
        lo, hi = [int(x) for x in re.findall(r"\d+", d["年龄范围"])[:2]]
        if lo <= xu_age <= hi:
            current = d["年龄范围"]
    rising_deg = member.get("rising_longitude")
    return {
        "bazi": member["bazi"],
        "shishen": member["shishen"],
        "cang": [[c["干"] for c in col["藏干"]] for col in member["canggan"]],
        "cang_ss": cang_ss,
        "nayin": member["nayins"],
        "wx": {k: member["wx"].get(k, 0) for k in WX_ORDER},
        "missing": member.get("missing_wx") or [],
        "bone": member["chenggu"],
        "zw": zw, "grid": grid, "sihua": sihua,
        "xu_age": xu_age, "current_dayun": current,
        "sun": f"{member['zodiac']} {member['sun_longitude'] % 30:.1f}°",
        "moon": f"{member['moon_sign']} {member['moon_deg_in_sign']:.1f}°",
        "asc": (f"{member['rising_sign']} {rising_deg % 30:.1f}°" if rising_deg is not None else "未计算（缺出生地坐标）"),
        "wuge": member.get("wuge"),
        "pillar_time": member.get("pillar_time") or {},
        "true_solar": member.get("true_solar_time") or {},
        "clock_alt": member.get("clock_alternative"),
        "warnings": member.get("warnings") or [],
    }


def sihua_line(f: dict) -> str:
    return "；".join(f"{k}{v['星曜']}→{v['所在宫位']}（{v['所在地支']}）" for k, v in f["zw"]["四化飞星"].items())


def time_note(member: dict, f: dict) -> str:
    pt, ts = f["pillar_time"], f["true_solar"]
    if pt.get("basis") != "true_solar":
        return "未取得出生地坐标，本盘按钟表时间排时柱；靠近时辰边界时结论可能偏一个时辰。"
    lon = ts.get("lon")
    note = (f"出生地经度约 {lon:.2f}°，经度修正 {ts['longitude_correction_min']:+.1f} 分钟，"
            f"均时差 {ts['equation_of_time_min']:+.1f} 分钟，钟表时间 {member['birth_time']} 对应真太阳时约 "
            f"{pt['time']}（{pt['shichen']}），距本时辰起点 {pt['minutes_from_shichen_start']:.0f} 分钟、"
            f"距终点 {pt['minutes_to_shichen_end']:.0f} 分钟。日柱、时柱、农历日、称骨与紫微时辰均按真太阳时；"
            "年柱、月柱按出生瞬间与节气时刻比较。")
    if pt.get("date") != member["solar_date"]:
        note += f"真太阳时已跨日至 {pt['date']}，日柱随之调整。"
    if pt.get("clock_tz_offset_hours") == 9.0:
        note += "出生时刻处于中国夏令时期间，已按 UTC+9 换算。"
    return note


def compare_rows(f: dict) -> list[tuple[str, str, str]]:
    alt = f["clock_alt"]
    if not alt:
        return []
    zw = f["zw"]
    main = "·".join(f["grid"]["命宫"]["main"]) or "借" + "·".join(f["grid"]["命宫"]["borrow"])
    return [
        ("时柱", f["bazi"][3], alt["时柱"]),
        ("命宫", f"{zw['命宫']} {main}", f"{alt['命宫']} {alt['命宫主星']}"),
        ("身宫", zw["身宫"], alt["身宫"]),
        ("称骨", f["bone"]["总重"], alt["称骨"]),
    ]


def pair_relation(a: dict, b: dict) -> dict:
    sx_score, sx_labels = _score_shengxiao_pair(a["bazi"][0][1], b["bazi"][0][1])
    rz_score, rz_label = _score_rizhu_pair(a["day_gan"], b["day_gan"])
    return {"sx": "、".join(sx_labels), "sx_score": sx_score, "rz": rz_label, "rz_score": rz_score}


# ---------------------------------------------------------------- validation

def validate(chart: dict, narrative: dict) -> None:
    try:
        import jsonschema
        schema = json.loads(NARRATIVE_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(narrative, schema)
    except ImportError:
        pass
    except Exception as exc:  # jsonschema.ValidationError
        raise ReportError(f"narrative 不符合契约：{getattr(exc, 'message', exc)}") from exc
    names = [m["name"] for m in chart["members"]]
    got = [p["name"] for p in narrative["persons"]]
    if got != names:
        raise ReportError(f"narrative.persons 与 chart.members 姓名或顺序不一致：{got} vs {names}")
    themes = [p["sketch"]["reconciliation"] for p in narrative["persons"]]
    rel = narrative.get("relation")
    if rel:
        themes.append(rel["reconciliation"])
        if rel["type"] == "synastry" and not chart.get("synastry"):
            raise ReportError("relation.type=synastry 需要多人 chart")
    for t in themes:
        if not RECONCILE_RE.search(t):
            raise ReportError(f"和解命题须为「与XX和解——不是YY，而是ZZ。」格式：{t}")
    for p in narrative["persons"]:
        for item in p["palace_readings"]:
            if item["palace"] not in PALACES:
                raise ReportError(f"未知宫位：{item['palace']}")


# ---------------------------------------------------------------- markdown

def t3_md(t: dict) -> list[str]:
    return [f"- ✦ 优势：{t['adv']}", f"- ⚠ 风险：{t['risk']}", f"- → 行动建议：{t['act']}"]


def wsum(signals: dict, weights: dict) -> float:
    keys = [k for k in weights if k in signals and weights[k] > 0]
    total = sum(weights[k] for k in keys)
    return round(sum(signals[k][0] * weights[k] for k in keys) / total, 1) if total else 0.0


def person_weights(member: dict, p: dict) -> dict:
    w = dict(p.get("weights") or DEFAULT_WEIGHTS)
    if not member.get("mbti"):
        w.pop("mbti", None)
    if not member.get("wuge"):
        w.pop("name", None)
    return w


def palace_label(f: dict, palace: str) -> str:
    cell = f["grid"][palace]
    if cell["main"]:
        return "·".join(s + (f"（化{f['sihua'][s]}）" if s in f["sihua"] else "") for s in cell["main"])
    return "借对宫" + "·".join(cell["borrow"])


def person_md(i: int, member: dict, p: dict, f: dict) -> list[str]:
    W = person_weights(member, p)
    zw = f["zw"]
    L = [f"## {i}. {member['name']} 个人命盘", "", "### 四柱八字", "",
         "| | 年柱 | 月柱 | 日柱 | 时柱 |", "|---|---|---|---|---|",
         "| 干支 | " + " | ".join(f["bazi"]) + " |",
         "| 天干十神 | " + " | ".join(f["shishen"]) + " |",
         "| 地支藏干 | " + " | ".join("、".join(x) for x in f["cang"]) + " |"]
    if f["cang_ss"]:
        L.append("| 藏干十神 | " + " | ".join("、".join(x) for x in f["cang_ss"]) + " |")
    L += ["| 纳音 | " + " | ".join(f["nayin"]) + " |", "",
          "五行统计：" + " · ".join(f"{k}{f['wx'][k]}" for k in WX_ORDER) + f"　｜　缺：{'、'.join(f['missing']) or '无'}", "",
          f"- 日主：{member['day_gan']}；旺衰：{p['strength']}", f"- 喜用方向：{p['favor']}", "", "五行解读：", ""]
    for t in p["wx_reading"]:
        L += t3_md(t)
    L += ["", "十神解读：", ""] + t3_md(p["shishen_reading"])
    b = f["bone"]
    L += ["", "### 袁天罡称骨", "", f"总重 **{b['总重']}**（{b['等级']}）｜年 {b['年']} · 月 {b['月']} · 日 {b['日']} · 时 {b['时']}", "",
          f"> {b['歌诀']}", ""] + t3_md(p["bone_reading"])
    L += ["", "### 紫微斗数", "",
          f"命宫 {zw['命宫']}｜身宫 {zw['身宫']}｜{zw['五行局']}｜命主 {zw['命主']}｜身主 {zw['身主']}｜大限{zw['大运方向']}", "",
          p["ming_reading"], "", "| 宫位 | 宫干支 | 主星 | 辅星 |", "|---|---|---|---|"]
    for palace in PALACES:
        c = f["grid"][palace]
        main = "、".join(c["main"]) or f"（无主星，借对宫{'·'.join(c['borrow'])}）"
        L.append(f"| {palace} | {c['gan']}{c['zhi']} | {main} | {'、'.join(c['aux']) or '—'} |")
    L += ["", f"四化飞星：{sihua_line(f)}", "", "格局识别：", ""]
    L += [f"- {name}：{desc}" for name, desc in zw.get("格局识别") or []] or ["- 未识别到内置格局"]
    L += [f"- {x}" for x in p.get("extra_patterns", [])]
    L += ["", "大限：" + "；".join(f"{d['年龄范围']} {d['宫位']}（{d['地支']}）" for d in zw["大限序列"][:6])
          + (f"。当前（虚岁{f['xu_age']}）处于 {f['current_dayun']}。" if f["current_dayun"] else f"。当前虚岁{f['xu_age']}，尚未起运（童限）。"),
          "", p["dayun_note"], "", "#### 六宫深度解读", ""]
    for item in p["palace_readings"]:
        L += [f"**{item['palace']}｜{palace_label(f, item['palace'])}**：{item['question']}", ""] + t3_md(item["triad"]) + [""]
    L += ["### 西洋星座", "", f"太阳 {f['sun']}｜月亮 {f['moon']}｜上升 {f['asc']}", ""] + t3_md(p["western_combo"])
    wg = f["wuge"]
    if wg and p.get("wuge_reading"):
        g = wg["五格"]
        strokes = " ".join(f"{x['字']}({x['康熙笔画']})" for x in wg["笔画明细"])
        L += ["", "### 三才五格", "", f"康熙笔画：{strokes}", "", "| 天格 | 人格 | 地格 | 总格 | 外格 |", "|---|---|---|---|---|",
              "| " + " | ".join(f"{g[k]['数理']}（{g[k]['吉凶']}）" for k in ["天格", "人格", "地格", "总格", "外格"]) + " |", "",
              f"三才 {wg['三才']['配置']}（三才评级：{wg['三才']['分析']['评级']}）｜综合评分 **{wg['综合评分']}**（{wg['综合评级']}）", ""] + t3_md(p["wuge_reading"])
    if p.get("mbti_note"):
        L += ["", "### MBTI 说明", "", p["mbti_note"]]
    L += ["", "### 六维度倾向（默认权重：" + "·".join(f"{SIGNAL_LABEL[k]}{v}" for k, v in W.items()) + "）", "",
          "| 维度 | 加权分 | 信号 | 综合 |", "|---|---|---|---|"]
    for key, label in DIMS:
        d = p["six_dimensions"][key]
        L.append(f"| {d.get('label', label)} | {wsum(d['signals'], W)} | " + "；".join(
            f"{SIGNAL_LABEL[k]}{d['signals'][k][0]}" for k in W if k in d["signals"]) + f" | {d['summary']} |")
    L += ["", f"### {p['advice_title']}", ""] + [f"- {x}" for x in p["advice"]]
    s = p["sketch"]
    L += ["", "### 人格速写", "", f"**内核**：{s['core']}", "", f"**命运**：{s['fate']}", "",
          f"**外在**：{s['outer']}", "", f"**和解命题**：{s['reconciliation']}", ""]
    return L


def render_md(chart: dict, nar: dict, F: list[dict]) -> str:
    members = chart["members"]
    L = [f"# {nar.get('title') or '天机 · ' + ' × '.join(m['name'] for m in members)}", ""]
    if nar.get("scenario"):
        L += [f"> 场景：{nar['scenario']}"] + ([">", f"> {nar['assumption']}"] if nar.get("assumption") else []) + [""]
    L += ["## 基本信息", "", "| 姓名 | 性别 | 公历出生（钟表时间） | 排盘时间 | 农历 | 出生地 | 生肖 |" + (" MBTI |" if any(m.get("mbti") for m in members) else ""),
          "|---|---|---|---|---|---|---|" + ("---|" if any(m.get("mbti") for m in members) else "")]
    for m, f in zip(members, F):
        pt = f["pillar_time"]
        basis = "真太阳时" if pt.get("basis") == "true_solar" else "钟表时间"
        row = (f"| {m['name']} | {m['gender']} | {m['solar_date']} {m['birth_time']} | {pt.get('time', m['birth_time'])}（{basis}·{pt.get('shichen', '')}） | "
               f"农历{m['lunar_month']}月{m['lunar_day']}日 | {m.get('birth_city') or '—'} | {m['shengxiao']} |")
        if any(x.get("mbti") for x in members):
            row += f" {m.get('mbti') or '—'} |"
        L.append(row)
    L += ["", "## 时辰说明", ""]
    for m, f in zip(members, F):
        L += [f"**{m['name']}**：{time_note(m, f)}", ""]
        rows = compare_rows(f)
        if rows:
            L += ["| 项目 | 真太阳时（采用） | 按钟表时间直排（对照） |", "|---|---|---|"] + [f"| {a} | {b} | {c} |" for a, b, c in rows] + [""]
    if nar.get("time_note"):
        L += [nar["time_note"], ""]
    L += ["## 置信度", "", "| 维度 | 置信度 | 主要影响因素 |", "|---|---|---|"] + [f"| {a} | {b} | {c} |" for a, b, c in nar["confidence"]] + [""]
    if nar.get("intro"):
        L += [nar["intro"], ""]
    for i, (m, p, f) in enumerate(zip(members, nar["persons"], F), 1):
        L += person_md(i, m, p, f)
    rel = nar.get("relation")
    n = len(members) + 1
    if rel and rel["type"] == "synastry":
        syn = chart["synastry"]
        L += [f"## {n}. 合盘", "", "| 维度 | 得分 | 满分 | 依据 |", "|---|---|---|---|"]
        L += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in synastry_rows(syn)]
        L += [f"| **合计** | **{syn['score']}** | {syn['max_possible']} | {syn['rating']} |", ""]
        if rel.get("score_note"):
            L += [rel["score_note"], ""]
        L += ["### 关系矩阵", "", "| 关系对 | 生肖 | 日主 |", "|---|---|---|"]
        for a, b, r in pairs(members):
            L.append(f"| {a['name']} × {b['name']} | {r['sx']} | {r['rz']} |")
        L += ["", "### 结构解读", ""]
        for t in rel["reading"]:
            L += t3_md(t)
        L += ["", f"- {rel['nourish']}", f"- {rel['drain']}", "", "### 时机窗口", "", rel["window"], "", "### 场景建议", ""]
        L += [f"**{a}**：{b}\n" for a, b in rel["advice"]]
        L += ["### 和解命题", "", f"> {rel['reconciliation']}", ""]
    elif rel and rel["type"] == "parent_child":
        L += [f"## {n}. {rel['title']}", "", rel["kid_core"], "", "| 维度 | 关系 |", "|---|---|"]
        L += [f"| {a} | {b} |" for a, b in rel["match"]]
        L += ["", f"- {rel['nourish']}", f"- {rel['suppress']}", "", "### 顺势养育建议", ""]
        L += [f"**{a}**：{b}\n" for a, b in rel["advice"]]
        L += ["### 和解命题", "", f"> {rel['reconciliation']}", ""]
    ft = nar["footer"]
    L += ["---", "", f"ℹ️ 本报告当前置信度约{ft['confidence_pct']}%。", f"影响精度的主要因素：{ft['factors']}",
          f"如需进一步校准，可以告诉我：{ft['questions']}", "", nar.get("disclaimer") or DISCLAIMER]
    return "\n".join(L) + "\n"


SYN_LABELS = [("wuxing_balance", "五行平衡"), ("wuxing_complete", "五行俱全"), ("shengxiao", "生肖关系"),
              ("riZhu", "日主生克"), ("chenggu", "称骨对比"), ("xingzuo", "星座相位"), ("xingming", "姓名合盘")]
SYN_MAX = {"wuxing_balance": 20, "wuxing_complete": 5, "shengxiao": 20, "riZhu": 20,
           "chenggu": 15, "xingzuo": 15, "xingming": 5}


def synastry_rows(syn: dict) -> list[tuple]:
    cs = syn["composite_scores"]
    return [(label, cs[k]["score"], SYN_MAX[k], cs[k]["comment"]) for k, label in SYN_LABELS if k in cs]


def pairs(members: list[dict]):
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            yield members[i], members[j], pair_relation(members[i], members[j])


# ---------------------------------------------------------------- html

def h(s) -> str:
    return html.escape(str(s), quote=True)


def t3_html(t: dict) -> str:
    return (f"<div class='t3'><p><b class='a'>✦ 优势</b>{h(t['adv'])}</p><p><b class='r'>⚠ 风险</b>{h(t['risk'])}</p>"
            f"<p><b class='s'>→ 行动建议</b>{h(t['act'])}</p></div>")


GRID = [["巳", "午", "未", "申"], ["辰", None, None, "酉"], ["卯", None, None, "戌"], ["寅", "丑", "子", "亥"]]

CSS = """*{box-sizing:border-box}body{margin:0;background:#faf7f2;color:#1a1410;font:15px/1.75 -apple-system,'PingFang SC','Noto Sans CJK SC','Microsoft YaHei',sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:24px 16px 64px}.hero{background:#1a1410;color:#faf7f2;border-radius:16px;padding:36px 28px;margin-bottom:20px}
.hero h1{margin:0 0 6px;font-size:28px;letter-spacing:.04em}.hero h1 span{color:#c9973a}.hero p{margin:4px 0;color:#d9cfbf}
.card{background:#fff;border:1px solid #ece3d3;border-radius:14px;padding:24px;margin:18px 0}h2{margin:0 0 4px;font-size:22px;border-left:4px solid #c9973a;padding-left:10px}
h3{margin:26px 0 10px;font-size:17px;color:#8a6420}.sub,.mut{color:#7a6e60;font-size:13px}.lbl{font-weight:600;color:#8a6420;margin:12px 0 4px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{border-bottom:1px solid #eee5d6;padding:8px;text-align:left;vertical-align:top}th{color:#8a6420;font-weight:600}
.pillars{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.pl{background:#faf7f2;border:1px solid #ece3d3;border-radius:10px;padding:12px 6px;text-align:center;display:flex;flex-direction:column}
.gz{font-size:28px;font-weight:700;letter-spacing:.1em}.bars{display:grid;gap:6px;max-width:520px}.bar{display:grid;grid-template-columns:28px 1fr 24px;align-items:center;gap:8px}
.track{height:10px;background:#f1eadf;border-radius:6px;overflow:hidden}.fill{height:100%;width:0;border-radius:6px;animation:g 1s ease forwards}@keyframes g{to{width:var(--w)}}
.wx0{background:#5c8a4e}.wx1{background:#c4553b}.wx2{background:#b08a4a}.wx3{background:#9aa0a6}.wx4{background:#3d6a8a}.gold{background:#c9973a}
.t3{background:#fbf8f3;border-left:3px solid #e4d4b4;border-radius:6px;padding:8px 14px;margin:8px 0}.t3 p{margin:4px 0}.t3 b{display:inline-block;min-width:88px;font-size:13px}.a{color:#5c8a4e}.r{color:#b5523a}.s{color:#8a6420}
.bone{display:flex;gap:18px;align-items:center}.big{font-size:40px;font-weight:700;color:#c9973a;white-space:nowrap}.song{font-family:serif;color:#5a4a36;margin:4px 0}
.chips{display:flex;flex-wrap:wrap;gap:8px}.chips span{background:#1a1410;color:#f3e7cf;border-radius:20px;padding:3px 12px;font-size:13px}
.zw{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin:14px 0}.zc{border:1px solid #e4d4b4;border-radius:8px;padding:8px;min-height:104px;background:#fff;font-size:13px}
.zc.center{grid-column:2/4;grid-row:2/4;background:#1a1410;color:#f3e7cf;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;gap:4px}.zc.center small{color:#cbbd9f}
.zc.empty{border-style:dashed;background:#fcfaf6}.zc.ming{box-shadow:inset 0 0 0 2px #c9973a}.pn{display:flex;justify-content:space-between;color:#8a6420;font-weight:600;margin-bottom:4px}.pn small{color:#a99a85}
.ms{display:inline-block;font-weight:700;margin-right:6px}.as{display:inline-block;color:#7a6e60;margin-right:5px;font-size:12px}i{font-style:normal;background:#c9973a;color:#fff;border-radius:3px;padding:0 3px;margin-left:1px;font-size:11px}
.em{color:#a99a85;font-size:12px}.tl{display:grid;gap:4px}.tli{padding:6px 10px;border-left:3px solid #e4d4b4;font-size:14px}.tli.cur{border-color:#c9973a;background:#fbf3e3}
details{border:1px solid #ece3d3;border-radius:8px;padding:8px 12px;margin:6px 0}summary{cursor:pointer}.q{color:#8a6420}
.wuge{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;text-align:center}.wuge div{background:#faf7f2;border-radius:8px;padding:8px;display:flex;flex-direction:column}.wuge b{font-size:22px}
.six{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.dim{border:1px solid #ece3d3;border-radius:10px;padding:12px}.dh{display:flex;justify-content:space-between}.sc{font-size:22px;font-weight:700;color:#c9973a}
.dim p{font-size:13px;margin:6px 0}.sg{display:grid;grid-template-columns:40px 1fr 28px;gap:6px;align-items:center;font-size:12px}.sg small{grid-column:1/4;color:#7a6e60;margin-bottom:4px}
.sk p{margin:8px 0}.sk b{color:#8a6420;margin-right:8px}blockquote{margin:14px 0 0;padding:14px 18px;background:#1a1410;color:#f3e7cf;border-radius:10px;font-family:serif;font-size:16px}
.score{display:grid;grid-template-columns:110px 1fr 70px;gap:10px;align-items:center;margin:6px 0;font-size:14px}.total{font-size:40px;font-weight:700;color:#c9973a}
.tabs{display:flex;gap:6px;flex-wrap:wrap}.tabs button{border:1px solid #c9973a;background:#fff;color:#8a6420;border-radius:20px;padding:4px 14px;cursor:pointer;font:inherit}.tabs button.on{background:#c9973a;color:#fff}
.tp{display:none;padding:12px 4px}.tp.on{display:block}.foot{font-size:13px;color:#7a6e60}
@media(max-width:640px){.six{grid-template-columns:1fr}.gz{font-size:22px}.zc{min-height:90px;font-size:11px;padding:5px}.wuge b{font-size:18px}}"""

JS = """document.querySelectorAll('.dim').forEach(d=>{const s=JSON.parse(d.dataset.s);const f=()=>{let t=0,w=0;d.querySelectorAll('input').forEach(i=>{t+=s[i.dataset.k]*+i.value;w+=+i.value});d.querySelector('.sc').textContent=w?(t/w).toFixed(1):'—';d.querySelector('.fill').style.width=(w?t/w:0)+'%'};d.querySelectorAll('input').forEach(i=>i.addEventListener('input',f))});
document.querySelectorAll('.tabgroup').forEach(g=>{const bs=g.querySelectorAll('.tabs button'),ps=g.querySelectorAll('.tp');bs.forEach((b,i)=>b.addEventListener('click',()=>{bs.forEach(x=>x.classList.remove('on'));ps.forEach(x=>x.classList.remove('on'));b.classList.add('on');ps[i].classList.add('on')}))});"""


def tabs_html(items) -> str:
    return ("<div class='tabgroup'><div class='tabs'>" + "".join(f"<button class='{'on' if i == 0 else ''}'>{h(a)}</button>" for i, (a, _) in enumerate(items))
            + "</div>" + "".join(f"<div class='tp {'on' if i == 0 else ''}'>{h(b)}</div>" for i, (_, b) in enumerate(items)) + "</div>")


def person_html(i: int, member: dict, p: dict, f: dict) -> str:
    W = person_weights(member, p)
    zw = f["zw"]
    mx = max(f["wx"].values()) or 1
    by_zhi = {c["zhi"]: (name, c) for name, c in f["grid"].items()}
    out = [f"<section class='card'><h2>{i}. {h(member['name'])} · 个人命盘</h2>",
           f"<p class='sub'>{h(member['solar_date'])} {h(member['birth_time'])}｜排盘 {h(f['pillar_time'].get('time', ''))} {h(f['pillar_time'].get('shichen', ''))}｜农历{member['lunar_month']}月{member['lunar_day']}日｜{h(member.get('birth_city') or '')}</p>",
           "<h3>四柱八字</h3><div class='pillars'>"]
    for k, label in enumerate(["年柱", "月柱", "日柱", "时柱"]):
        ss = "·".join(f["cang_ss"][k]) if f["cang_ss"] else ""
        out.append(f"<div class='pl'><small>{label}</small><div class='gz'>{h(f['bazi'][k])}</div><small>{h(f['shishen'][k])}</small>"
                   f"<small class='mut'>藏 {h('·'.join(f['cang'][k]))}</small><small class='mut'>{h(ss)}</small><small class='mut'>{h(f['nayin'][k])}</small></div>")
    out.append("</div><h3>五行分布</h3><div class='bars'>")
    for k, wx in enumerate(WX_ORDER):
        v = f["wx"][wx]
        out.append(f"<div class='bar'><span>{wx}</span><div class='track'><div class='fill wx{k}' style='--w:{v / mx * 100:.0f}%'></div></div><b>{v}</b></div>")
    out.append(f"</div><p><b>日主</b> {h(member['day_gan'])}　<b>旺衰</b> {h(p['strength'])}<br><b>喜用</b> {h(p['favor'])}　<b>缺</b> {h('、'.join(f['missing']) or '无')}</p>")
    out += [t3_html(t) for t in p["wx_reading"]] + ["<p class='lbl'>十神</p>", t3_html(p["shishen_reading"])]
    b = f["bone"]
    out.append(f"<h3>袁天罡称骨</h3><div class='bone'><div class='big'>{h(b['总重'])}</div><div><b>{h(b['等级'])}</b>　<span class='mut'>年{h(b['年'])} · 月{h(b['月'])} · 日{h(b['日'])} · 时{h(b['时'])}</span>"
               f"<p class='song'>{h(b['歌诀'])}</p></div></div>{t3_html(p['bone_reading'])}")
    out.append(f"<h3>紫微斗数</h3><div class='chips'><span>命宫 {h(zw['命宫'])}</span><span>身宫 {h(zw['身宫'])}</span><span>{h(zw['五行局'])}</span>"
               f"<span>命主 {h(zw['命主'])}</span><span>身主 {h(zw['身主'])}</span><span>大限{h(zw['大运方向'])}</span></div><p>{h(p['ming_reading'])}</p><div class='zw'>")
    for r, row in enumerate(GRID):
        for c, zhi in enumerate(row):
            if zhi is None:
                if r == 1 and c == 1:
                    out.append(f"<div class='zc center'><b>{h(member['name'])}</b><small>{h(zw['五行局'])} · 命主{h(zw['命主'])} · 身主{h(zw['身主'])}</small><small>{h(sihua_line(f))}</small></div>")
                continue
            name, cell = by_zhi[zhi]
            mark = lambda s: f"<i>{h(f['sihua'][s])}</i>" if s in f["sihua"] else ""
            stars = "".join(f"<span class='ms'>{h(s)}{mark(s)}</span>" for s in cell["main"]) or f"<span class='em'>空宫 · 借{h('·'.join(cell['borrow']))}</span>"
            aux = "".join(f"<span class='as'>{h(s)}{mark(s)}</span>" for s in cell["aux"])
            cls = "zc" + (" empty" if not cell["main"] else "") + (" ming" if name == "命宫" else "")
            out.append(f"<div class='{cls}'><div class='pn'>{h(name)}<small>{h(cell['gan'] + zhi)}</small></div>{stars}<div>{aux}</div></div>")
    out.append("</div><p class='lbl'>格局</p><ul>" + ("".join(f"<li>{h(n)}：{h(d)}</li>" for n, d in zw.get("格局识别") or []) or "<li>未识别到内置格局</li>")
               + "".join(f"<li>{h(x)}</li>" for x in p.get("extra_patterns", [])) + "</ul><p class='lbl'>大限</p><div class='tl'>")
    for d in zw["大限序列"][:6]:
        cur = " cur" if d["年龄范围"] == f["current_dayun"] else ""
        mains = "·".join(s for s in d["主星"] if s in MAJOR) or "借对宫" + "·".join(f["grid"][OPPOSITE[d["宫位"]]]["main"])
        out.append(f"<div class='tli{cur}'><b>{h(d['年龄范围'])}</b> {h(d['宫位'])}（{h(d['地支'])}）{h(mains)}</div>")
    out.append(f"</div><p>{h(p['dayun_note'])}</p><h3>六宫深度解读</h3>")
    for item in p["palace_readings"]:
        out.append(f"<details><summary><b>{h(item['palace'])}</b>｜{h(palace_label(f, item['palace']))}</summary><p class='q'>{h(item['question'])}</p>{t3_html(item['triad'])}</details>")
    out.append(f"<h3>西洋星座</h3><div class='chips'><span>☉ 太阳 {h(f['sun'])}</span><span>☽ 月亮 {h(f['moon'])}</span><span>↑ 上升 {h(f['asc'])}</span></div>{t3_html(p['western_combo'])}")
    wg = f["wuge"]
    if wg and p.get("wuge_reading"):
        g = wg["五格"]
        strokes = " ".join(f"{x['字']}({x['康熙笔画']})" for x in wg["笔画明细"])
        out.append(f"<h3>三才五格</h3><p class='mut'>康熙笔画：{h(strokes)}</p><div class='wuge'>"
                   + "".join(f"<div><small>{k}</small><b>{g[k]['数理']}</b><small>{h(g[k]['吉凶'])}</small></div>" for k in ["天格", "人格", "地格", "总格", "外格"])
                   + f"</div><p>三才 <b>{h(wg['三才']['配置'])}</b>（{h(wg['三才']['分析']['评级'])}）｜综合 <b>{h(wg['综合评分'])}</b>（{h(wg['综合评级'])}）</p>{t3_html(p['wuge_reading'])}")
    if p.get("mbti_note"):
        out.append(f"<h3>MBTI 说明</h3><p>{h(p['mbti_note'])}</p>")
    out.append("<h3>六维度倾向</h3><p class='mut'>拖动滑块调整权重，分数实时重算。</p><div class='six'>")
    for key, label in DIMS:
        d = p["six_dimensions"][key]
        sig = d["signals"]
        data = h(json.dumps({k: sig[k][0] for k in W if k in sig}))
        rows = "".join(f"<div class='sg'><span>{SIGNAL_LABEL[k]}</span><input type='range' min='0' max='50' value='{W[k]}' data-k='{k}'><em>{sig[k][0]}</em><small>{h(sig[k][1])}</small></div>" for k in W if k in sig)
        score = wsum(sig, W)
        out.append(f"<div class='dim' data-s='{data}'><div class='dh'><b>{h(d.get('label', label))}</b><span class='sc'>{score}</span></div><div class='track'><div class='fill gold' style='--w:{score}%'></div></div>"
                   f"<p>{h(d['summary'])}</p><details><summary>信号与权重</summary>{rows}</details></div>")
    out.append(f"</div><h3>{h(p['advice_title'])}</h3><ul>" + "".join(f"<li>{h(x)}</li>" for x in p["advice"]) + "</ul>")
    s = p["sketch"]
    out.append(f"<h3>人格速写</h3><div class='sk'><p><b>内核</b>{h(s['core'])}</p><p><b>命运</b>{h(s['fate'])}</p><p><b>外在</b>{h(s['outer'])}</p></div><blockquote>{h(s['reconciliation'])}</blockquote></section>")
    return "".join(out)


def render_html(chart: dict, nar: dict, F: list[dict]) -> str:
    members = chart["members"]
    names = " × ".join(m["name"] for m in members)
    title = nar.get("title") or f"天机 · {names}"
    o = [f"<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{h(title)}</title><style>{CSS}</style></head><body><div class='wrap'>",
         f"<div class='hero'><h1>天机 · <span>{h(names)}</span></h1>"
         + (f"<p>{h(nar['scenario'])}</p>" if nar.get("scenario") else "") + (f"<p>{h(nar['assumption'])}</p>" if nar.get("assumption") else "") + "</div>",
         "<section class='card'><h2>基本信息与置信度</h2><table><tr><th>姓名</th><th>公历（钟表）</th><th>排盘时间</th><th>农历</th><th>出生地</th><th>生肖</th></tr>"]
    for m, f in zip(members, F):
        pt = f["pillar_time"]
        o.append(f"<tr><td>{h(m['name'])}（{h(m['gender'])}）{(' · ' + h(m['mbti'])) if m.get('mbti') else ''}</td><td>{h(m['solar_date'])} {h(m['birth_time'])}</td>"
                 f"<td>{h(pt.get('time', ''))} {h(pt.get('shichen', ''))}</td><td>{m['lunar_month']}月{m['lunar_day']}日</td><td>{h(m.get('birth_city') or '—')}</td><td>{h(m['shengxiao'])}</td></tr>")
    o.append("</table><h3>时辰说明</h3>")
    for m, f in zip(members, F):
        o.append(f"<p><b>{h(m['name'])}</b>：{h(time_note(m, f))}</p>")
        rows = compare_rows(f)
        if rows:
            o.append("<table><tr><th>项目</th><th>真太阳时（采用）</th><th>按钟表时间直排（对照）</th></tr>" + "".join(f"<tr><td>{h(a)}</td><td>{h(b)}</td><td class='mut'>{h(c)}</td></tr>" for a, b, c in rows) + "</table>")
    if nar.get("time_note"):
        o.append(f"<p>{h(nar['time_note'])}</p>")
    o.append("<h3>置信度</h3><table><tr><th>维度</th><th>置信度</th><th>主要影响因素</th></tr>" + "".join(f"<tr><td>{h(a)}</td><td style='color:#c9973a'>{h(b)}</td><td>{h(c)}</td></tr>" for a, b, c in nar["confidence"])
             + "</table>" + (f"<p class='mut'>{h(nar['intro'])}</p>" if nar.get("intro") else "") + "</section>")
    rel = nar.get("relation")
    if rel and rel["type"] == "synastry":
        syn = chart["synastry"]
        o.append(f"<section class='card'><h2>合盘总览</h2><div style='display:flex;gap:20px;align-items:center'><div class='total'>{h(syn['score'])}</div><div><b>{h(syn['rating'])}</b>"
                 + (f"<p class='mut'>{h(rel['score_note'])}</p>" if rel.get("score_note") else "") + "</div></div>")
        for a, b, c, d in synastry_rows(syn):
            o.append(f"<div class='score'><span>{h(a)}</span><div class='track'><div class='fill gold' style='--w:{b / c * 100:.0f}%'></div></div><b>{h(b)}/{c}</b></div><p class='mut' style='margin:-4px 0 6px 120px'>{h(d)}</p>")
        o.append("<h3>关系矩阵</h3><table><tr><th>关系对</th><th>生肖</th><th>日主</th></tr>" + "".join(f"<tr><td>{h(a['name'])} × {h(b['name'])}</td><td>{h(r['sx'])}</td><td>{h(r['rz'])}</td></tr>" for a, b, r in pairs(members)) + "</table>")
        o.append("<h3>结构解读</h3>" + "".join(t3_html(t) for t in rel["reading"]) + f"<p>{h(rel['nourish'])}</p><p>{h(rel['drain'])}</p><h3>时机窗口</h3><p>{h(rel['window'])}</p><h3>场景建议</h3>"
                 + tabs_html(rel["advice"]) + f"<blockquote>{h(rel['reconciliation'])}</blockquote></section>")
    for i, (m, p, f) in enumerate(zip(members, nar["persons"], F), 1):
        o.append(person_html(i, m, p, f))
    if rel and rel["type"] == "parent_child":
        o.append(f"<section class='card'><h2>{len(members) + 1}. {h(rel['title'])}</h2><p>{h(rel['kid_core'])}</p><table>" + "".join(f"<tr><th style='width:70px'>{h(a)}</th><td>{h(b)}</td></tr>" for a, b in rel["match"])
                 + f"</table><div class='t3'><p><b class='a'>滋养</b>{h(rel['nourish'])}</p><p><b class='r'>压制</b>{h(rel['suppress'])}</p></div><h3>顺势养育建议</h3>"
                 + tabs_html(rel["advice"]) + f"<blockquote>{h(rel['reconciliation'])}</blockquote></section>")
    ft = nar["footer"]
    o.append(f"<section class='card foot'><p>ℹ️ 本报告当前置信度约{h(ft['confidence_pct'])}%。影响精度的主要因素：{h(ft['factors'])}如需进一步校准，可以告诉我：{h(ft['questions'])}</p><p>{h(nar.get('disclaimer') or DISCLAIMER)}</p></section>")
    o.append(f"</div><script>{JS}</script></body></html>")
    return "".join(o)


# ---------------------------------------------------------------- entry

def render(chart: dict, narrative: dict, as_of_year: int | None = None) -> tuple[str, str]:
    validate(chart, narrative)
    year = as_of_year or datetime.date.today().year
    F = [facts(m, year) for m in chart["members"]]
    return render_md(chart, narrative, F), render_html(chart, narrative, F)


def main() -> None:
    ap = argparse.ArgumentParser(description="天机固定报告格式渲染（Markdown + HTML）")
    ap.add_argument("--chart", required=True, type=Path)
    ap.add_argument("--narrative", required=True, type=Path)
    ap.add_argument("--output-dir", type=Path, default=Path("tianji-output"))
    ap.add_argument("--basename", default="tianji_report")
    ap.add_argument("--as-of-year", type=int, help="计算当前大限所用年份，默认今年")
    args = ap.parse_args()
    chart = json.loads(args.chart.read_text(encoding="utf-8"))
    narrative = json.loads(args.narrative.read_text(encoding="utf-8"))
    md, page = render(chart, narrative, args.as_of_year)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / f"{args.basename}.md").write_text(md, encoding="utf-8")
    (args.output_dir / f"{args.basename}.html").write_text(page, encoding="utf-8")
    print(f"[天机] 报告已生成：{args.output_dir / (args.basename + '.md')}、{args.output_dir / (args.basename + '.html')}")


if __name__ == "__main__":
    main()
