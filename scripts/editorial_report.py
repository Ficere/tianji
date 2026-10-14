#!/usr/bin/env python3
"""固定编辑式报告：chart 事实 + narrative 解读 -> 同内容 Markdown/HTML/PDF。"""
from __future__ import annotations

import datetime
import html
import re
from pathlib import Path

from render_report import (
    DISCLAIMER, PALACES, WX_ORDER, ReportError, compare_rows, facts,
    pairs, sihua_line, synastry_rows, time_note, validate,
)

ROOT = Path(__file__).resolve().parent.parent
CSS_PATH = ROOT / "assets/editorial-report.css"
MARRIAGE_TOPICS = ("钱与债务", "居住与工作", "家务与照护", "双方父母边界", "生育与亲密", "冲突与安全")


def cell(value) -> str:
    return str(value).replace("|", r"\|").replace("\n", " ")


def table(headers, rows) -> list[str]:
    return ["| " + " | ".join(map(cell, headers)) + " |",
            "| " + " | ".join("---" for _ in headers) + " |"] + [
        "| " + " | ".join(map(cell, row)) + " |" for row in rows]


def triad(value: dict) -> list[str]:
    return [f"- **优势：** {value['adv']}", f"- **风险：** {value['risk']}",
            f"- **行动建议：** {value['act']}", ""]


def is_assumed(member: dict) -> bool:
    return member.get("birth_time_source") == "assumed"


def named(member: dict) -> str:
    return cell(member["name"]) + ("【假设盘】" if is_assumed(member) else "")


def assumption_notice(chart: dict) -> str:
    notes = [f"{m['name']}按用户指定 {m['birth_time']} 假设时刻计算，真实出生时辰未知。"
             f"{m.get('birth_time_note', '')}" for m in chart["members"] if is_assumed(m)]
    if not notes:
        return ""
    return (" ".join(notes) +
            "时柱、紫微、称骨、月亮、上升、起运、大限及合盘分项均为条件结果；"
            "日柱还需排除真太阳午夜跨日。输出完整不代表输入已核实。")


def validate_editorial(chart: dict, nar: dict) -> None:
    validate(chart, nar)
    for member in chart["members"]:
        if is_assumed(member) and not member.get("birth_time_note"):
            raise ReportError("假设盘缺 birth_time_note；请记录真实时辰未知与用户指定依据")
    editorial = nar.get("editorial") or {}
    stage = editorial.get("stage", "")
    if "结婚" in stage or "婚前" in stage:
        if len(chart["members"]) != 2 or not chart.get("synastry"):
            raise ReportError("婚前伴侣报告需要两人及合盘计算")
        titles = {s["title"] for s in editorial.get("cooperation_sections", [])}
        missing = set(MARRIAGE_TOPICS) - titles
        if missing:
            raise ReportError("婚前报告缺协作主题：" + "、".join(sorted(missing)))
    if chart.get("synastry") and not nar.get("relation"):
        raise ReportError("多人编辑式报告必须提供 relation，不能只有机械评分")


def current_limit(f: dict) -> str:
    current = next((d for d in f["zw"]["大限序列"]
                    if d["年龄范围"] == f["current_dayun"]), None)
    return (f"{current['年龄范围']} {current['宫位']}" if current
            else f"虚岁{f['xu_age']}，尚未起运（童限）")


def person_lines(member: dict, p: dict, f: dict) -> list[str]:
    label = named(member)
    L = [f"### {label}", ""]
    if is_assumed(member):
        L += [f"> 本章依赖用户指定 {member['birth_time']} 假设时刻，不是已核实的出生盘。", ""]
    L += ["八字：" + " · ".join(f["bazi"]) + "；纳音：" + "／".join(f["nayin"]) + "。",
          "", "天干十神：" + "／".join(f["shishen"]) + "。", "",
          "藏干／十神：" + "；".join(
              "、".join(c["干"] + "（" + c["十神"] + "）" for c in col["藏干"])
              for col in (member.get("deep") or {}).get("canggan_shishen", {}).get("四柱藏干", [])) + "。",
          "", "表层五行：" + " · ".join(f"{w}{f['wx'][w]}" for w in WX_ORDER) +
          "。计数为零不等于藏干不存在，不等于旺衰力量。",
          "", f"日主：{member['day_gan']}；{p['strength']}。喜用：{p['favor']}", ""]
    for value in p["wx_reading"]:
        L += triad(value)
    L += ["#### 十神与相处观察", ""] + triad(p["shishen_reading"])
    b = f["bone"]
    L += ["#### 称骨", "", f"{b['年']} + {b['月']} + {b['日']} + {b['时']} = "
          f"**{b['总重']}**，脚本分类“{b['等级']}”。", "", f"> {b['歌诀']}", "",
          "歌诀是历史民俗文本，不按字面承诺财富、要求离家或判断婚姻价值。", ""]
    L += triad(p["bone_reading"])
    zw = f["zw"]
    L += ["#### 紫微", "", f"命宫 {zw['命宫']}；身宫 {zw['身宫']}；{zw['五行局']}；"
          f"命主 {zw['命主']}，身主 {zw['身主']}。", "",
          p["ming_reading"], "", "四化：" + sihua_line(f), ""]
    for reading in p["palace_readings"]:
        palace = reading["palace"]
        g = f["grid"][palace]
        main = "、".join(g["main"]) or "无十四主星，借对宫" + "、".join(g["borrow"])
        L += [f"#### {palace}：{main}", "", reading["question"], ""] + triad(reading["triad"])
    patterns = zw.get("格局识别") or []
    if patterns or p.get("extra_patterns"):
        L += ["#### 格局记录", ""] + [f"- {name}：{desc}" for name, desc in patterns]
        L += [f"- {x}" for x in p.get("extra_patterns", [])] + [""]
    L += ["#### 当前阶段", "", f"当前虚岁 {f['xu_age']}，紫微大限为 {current_limit(f)}。",
          "", p["dayun_note"], "", "#### 星座组合", "",
          f"太阳 {f['sun']} × 月亮 {f['moon']} × 上升 {f['asc']}。", ""]
    L += triad(p["western_combo"])
    if f["wuge"]:
        wg = f["wuge"]
        L += ["#### 姓名民俗数理", "",
              "康熙笔画：" + "、".join(f"{x['字']}({x['康熙笔画']})" for x in wg["笔画明细"]), "",
              f"三才评级 {wg['三才']['分析']['评级']}；综合评分 {wg['综合评分']}（{wg['综合评级']}）。", ""]
        L += table(["格", "数理", "民俗标签"],
                   [(k, wg["五格"][k]["数理"], wg["五格"][k]["吉凶"]) for k in
                    ("天格", "人格", "地格", "总格", "外格")]) + [""]
        if p.get("wuge_reading"):
            L += triad(p["wuge_reading"])
    if p.get("mbti_note"):
        L += ["#### 自报 MBTI", "", p["mbti_note"], ""]
    L += [f"#### {p['advice_title']}", ""] + [f"- {item}" for item in p["advice"]] + [""]
    sketch = p["sketch"]
    L += ["#### 人格速写", "", f"- **内核：** {sketch['core']}",
          f"- **阶段主题：** {sketch['fate']}", f"- **外在：** {sketch['outer']}",
          f"- **和解命题：** {sketch['reconciliation']}", ""]
    return L


def markdown_report(chart: dict, nar: dict, F: list[dict]) -> str:
    members = chart["members"]
    ed = nar.get("editorial") or {}
    title = nar.get("title") or "天机 · " + " × ".join(m["name"] for m in members)
    notice = assumption_notice(chart)
    L = [f"# {cell(title)}", ""]
    if ed.get("subtitle"):
        L += [f"> {ed['subtitle']}", ""]
    L += [f"场景：{nar.get('scenario') or ('个人' if len(members) == 1 else '多人合盘')}。"
          + (f"当前阶段：{ed['stage']}。" if ed.get("stage") else ""), ""]
    if nar.get("assumption"):
        L += [nar["assumption"], ""]
    if notice:
        L += [f"> **假设时辰说明：** {notice}", ""]
    L += [nar.get("disclaimer") or DISCLAIMER,
          "", "计算可复现性不等于命理具有科学预测效度；分数不是成功概率，不用于劝婚或劝退。", "",
          "## 基础信息与置信度", ""]
    L += table(["成员", "出生日期／钟表时间", "出生地", "排盘时间"],
               [(named(m), m["solar_date"] + " " + m["birth_time"] +
                 ("【假设】" if is_assumed(m) else ""), m.get("birth_city") or "坐标定位",
                 f["pillar_time"].get("date", m["solar_date"]) + " " +
                 f["pillar_time"].get("time", m["birth_time"]) +
                 "（" + {"true_solar": "真太阳时", "clock": "钟表时间"}.get(
                     f["pillar_time"].get("basis"), "钟表时间") + "·" +
                 f["pillar_time"].get("shichen", "") + "）") for m, f in zip(members, F)])
    L += [""] + table(["成员", "四柱", "农历／生肖"],
                      [(named(m), " · ".join(f["bazi"]),
                        f"农历{m['lunar_month']}月{m['lunar_day']}日／{m['shengxiao']}")
                       for m, f in zip(members, F)]) + [""]
    L += table(["维度", "输入／计算状态", "影响因素"], nar["confidence"]) + [""]
    for m in members:
        if is_assumed(m):
            L += [f"- **{cell(m['name'])}输入边界：** 年月与太阳可按日期检查；"
                  "日柱保留午夜跨日可能，其他涉及时辰项及合盘仅为条件结果。", ""]
    L += ["### 时辰与坐标的关键说明", ""]
    for m, f in zip(members, F):
        L += [f"- **{named(m)}：** {time_note(m, f)}", ""]
        alt = compare_rows(f)
        if alt:
            L += table(["项目", "真太阳时采用", "钟表时间对照"], alt) + [""]
    for source in ed.get("coordinate_sources", []):
        L += [f"{source['name']}：{source['note']}（[{source['name']}坐标说明]({source['url']})）。"
              f"网址：{source['url']}", ""]
    L += ["晚子时采用不换日柱约定；对比其他工具时，先统一日界与时钟口径。", ""]
    if nar.get("time_note"):
        L += [nar["time_note"], ""]
    if nar.get("intro"):
        L += [nar["intro"], ""]
    L += ["## 个人命盘", ""]
    for m, p, f in zip(members, nar["persons"], F):
        L += person_lines(m, p, f)
    syn = chart.get("synastry")
    relation = nar.get("relation")
    if syn:
        scene = nar.get("scenario", "")
        relation_title = ("伴侣合盘" if "情侣" in scene or "伴侣" in scene else
                          "家庭合盘" if "亲子" in scene or "家庭" in scene else "场景合盘")
        L += ["## " + relation_title + ("【假设输入】" if notice else ""), "", "### 五行能量地图", ""]
        if len(members) <= 2:
            L += table(["五行"] + [named(m) for m in members] + ["合计"],
                       [(w, *[f["wx"][w] for f in F], sum(f["wx"][w] for f in F)) for w in WX_ORDER])
        else:
            L += table(["五行", "各成员表层统计", "合计"],
                       [(w, "；".join(f"{named(m)} {f['wx'][w]}" for m, f in zip(members, F)),
                         sum(f["wx"][w] for f in F)) for w in WX_ORDER])
        L += ["", "表层为零不等于藏干没有；简单计数不是旺衰、人格或能力量表。", "",
              "### 能量流向与结构解读", ""]
        if relation["type"] == "synastry":
            for item in relation["reading"]:
                L += triad(item)
            L += [relation["nourish"], "", relation["drain"], ""]
        else:
            L += [relation["kid_core"], "", relation["nourish"], "", relation["suppress"], ""]
            L += table(["观察维度", "亲子关系"], relation["match"]) + [""]
        L += ["### 关系矩阵", ""]
        L += table(["关系对", "生肖分类", "日主分类"],
                   [(named(a) + " × " + named(b), r["sx"], r["rz"]) for a, b, r in pairs(members)])
        L += ["", "日主相克不等于克夫或克妻，不决定掌权或责任；太阳星座分项是整宫类别，"
              "不是精确黄经相位，也不冒充全行星专业西洋合盘。", "",
              "### 确定性评分" + ("【条件结果】" if notice else ""), ""]
        L += table(["维度", "得分／满分", "脚本口径"],
                   [(a, f"{b}／{c}", d) for a, b, c, d in synastry_rows(syn)])
        L += [f"| 合计 | {syn['score']}／{syn['max_possible']} | 机械分类：{syn['rating']} |", "",
              "不将机械标签转译为婚姻或人格等级；归一化百分比不是关系成功率。", ""]
        if relation.get("score_note"):
            L += [relation["score_note"], ""]
    L += ["## " + ed.get("cooperation_title", "场景协作指南"), ""]
    for section in ed.get("cooperation_sections", []):
        L += [f"### {section['title']}", "", section["text"], ""]
        L += [f"- {item}" for item in section.get("items", [])] + [""]
    if relation:
        L += ["### 具体协作与现实验证", ""]
        L += [f"- **{a}：** {b}" for a, b in relation["advice"]] + [""]
    elif not ed.get("cooperation_sections"):
        for m, p in zip(members, nar["persons"]):
            L += [f"### {named(m)}", ""] + [f"- {v}" for v in p["advice"]] + [""]
    L += ["## 当前阶段与时间线", ""]
    rows = []
    for m, f in zip(members, F):
        dy = (m.get("deep") or {}).get("dayun") or {}
        cur = dy.get("当前大运")
        rows.append((named(m), dy.get("起运", {}).get("折算说明", "未计算"),
                     f"{cur['干支']}（约{cur['起始年龄']:.2f}–{cur['结束年龄']:.2f}岁；"
                     f"{cur['起止公历']}）" if cur else "未计算",
                     current_limit(f)))
    L += table(["成员", "八字起运", "当前八字大运", "当前紫微大限"], rows) + [""]
    L += ["### 未来三年：体系内关系记录", ""]
    for m in members:
        dy = (m.get("deep") or {}).get("dayun") or {}
        L += [f"#### {named(m)}", ""]
        L += table(["年份", "脚本标签", "与原局关系"],
                   [(str(y["年份"]) + " " + y["干支"], y["喜忌"],
                     "；".join(y.get("与原局") or []) or "未列特殊关系")
                    for y in dy.get("未来三年", [])]) + [""]
    L += ["紫微按虚岁、八字按节令起运，口径不同。顺逆、冲刑合害不是事件预测，"
          "不用于改变婚期、预测疾病、离婚或子女；现实安排优先。", ""]
    if relation and relation["type"] == "synastry":
        L += [relation["window"], ""]
    L += ["## 和解命题与校准", ""]
    for p in nar["persons"]:
        L += [f"> {p['name']}：{p['sketch']['reconciliation']}", ""]
    if relation:
        L += [f"> {relation['reconciliation']}", ""]
    L += ["### 输入校准与现实反证", "", nar["footer"]["factors"], "",
          nar["footer"]["questions"], "",
          "若实际行为与民俗叙事不符，以真实经历为准；不提供总体预测置信度百分比。", "",
          "## 附录：紫微十二宫结构", ""]
    for m, f in zip(members, F):
        L += [f"### {named(m)}", ""]
        L += table(["宫位／干支", "十四主星", "辅星"],
                   [(p + "／" + g["gan"] + g["zhi"],
                     "、".join(g["main"]) or "无主星，借" + "、".join(g["borrow"]),
                     "、".join(g["aux"]) or "无")
                    for p, g in f["grid"].items()]) + [""]
    L += [nar.get("disclaimer") or DISCLAIMER, ""]
    return "\n".join(L)


def html_report(md: str, chart: dict, nar: dict) -> str:
    try:
        import bleach
        import markdown
    except ImportError as exc:
        raise ReportError("editorial 需要 Markdown 与 bleach：pip install -r requirements.txt") from exc
    # Keep Markdown quote markers while escaping every HTML opening delimiter.
    escaped_md = html.escape(md, quote=False).replace("&gt;", ">")
    body = markdown.markdown(escaped_md, extensions=["tables"])
    tags = {"p", "h1", "h2", "h3", "h4", "ul", "ol", "li", "strong", "em", "blockquote",
            "table", "thead", "tbody", "tr", "th", "td", "a", "hr", "br", "code"}
    body = bleach.clean(body, tags=tags, attributes={"a": ["href", "title"]},
                        protocols=["http", "https"], strip=True)
    # Group short score/appendix units after sanitization, not untrusted markup.
    body = re.sub(r"(<h3>确定性评分[^<]*</h3>.*?)(?=<h2>)",
                  r"<section class='reading-unit'>\1</section>", body, flags=re.S)
    body = re.sub(r"(<h3>时辰与坐标的关键说明</h3>.*?)(?=<h2>)",
                  r"<section class='reading-unit'>\1</section>", body, flags=re.S)
    appendix = "<h2>附录：紫微十二宫结构</h2>"
    if appendix in body:
        before, after = body.split(appendix, 1)
        after = re.sub(r"(<h3>[^<]*</h3>\s*<table>.*?</table>)",
                       r"<section class='reading-unit'>\1</section>", after, flags=re.S)
        body = before + appendix + after
    title = nar.get("title") or "天机 · 场景合盘"
    ed = nar.get("editorial") or {}
    notice = assumption_notice(chart)
    marker = "含用户指定假设时刻" if notice else ""
    if notice:
        marker = "；".join(f"{m['name']} {m['birth_time']} 假设" for m in chart["members"] if is_assumed(m))
    cover = (f"<header class='cover'><div class='brand'>天机 · 文化参考</div>"
             f"<h1>{html.escape(title)}</h1><p>{html.escape(ed.get('subtitle', ''))}</p>"
             + (f"<p class='notice'>{html.escape(notice)}</p>" if notice else "") +
             f"<p>{datetime.date.today().isoformat()}</p></header>")
    css = CSS_PATH.read_text(encoding="utf-8")
    return ("<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<meta name='author' content='Perplexity Computer'>"
            f"<title>{html.escape(title)}</title><style>{css}</style></head>"
            f"<body><div class='report'>{cover}<div class='assumption-marker' "
            f"data-label='{html.escape(marker, quote=True)}'></div><main>{body}</main></div></body></html>")


def render(chart: dict, narrative: dict, as_of_year: int | None = None) -> tuple[str, str]:
    validate_editorial(chart, narrative)
    year = as_of_year or datetime.date.today().year
    F = [facts(m, year) for m in chart["members"]]
    md = markdown_report(chart, narrative, F)
    return md, html_report(md, chart, narrative)


def write_pdf(page: str, output: Path) -> None:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise ReportError("PDF 需要 WeasyPrint：pip install -r requirements-report.txt") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=page, base_url=str(ROOT)).write_pdf(str(output))
    if not output.is_file() or output.stat().st_size == 0:
        raise ReportError("PDF 输出为空")
