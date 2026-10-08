#!/usr/bin/env python3
"""固定报告格式：事实取自 chart、解读取自 narrative、校验与转义。"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fortune_calc import analyze_person, analyze_synastry  # noqa: E402
from render_report import ReportError, render  # noqa: E402
from tianji import run_pipeline  # noqa: E402

EXAMPLE_INPUT = ROOT / "examples" / "report" / "example_members.json"
EXAMPLE_NARRATIVE = ROOT / "examples" / "report" / "example_narrative.json"


def load_example():
    return json.loads(EXAMPLE_NARRATIVE.read_text(encoding="utf-8"))


def person_narrative(name: str) -> dict:
    p = copy.deepcopy(load_example()["persons"][0])
    p["name"] = name
    p.pop("mbti_note", None)
    return p


class ExampleReportTests(unittest.TestCase):
    def test_pipeline_renders_fixed_format_from_chart_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = run_pipeline(EXAMPLE_INPUT, Path(tmp), narrative_path=EXAMPLE_NARRATIVE, as_of_year=2026)
            md = paths["final_md"].read_text(encoding="utf-8")
            page = paths["final_html"].read_text(encoding="utf-8")
            chart = json.loads(paths["chart"].read_text(encoding="utf-8"))
        m = chart["members"][0]
        self.assertIn("| 干支 | " + " | ".join(m["bazi"]) + " |", md)
        self.assertIn(m["chenggu"]["歌诀"], md)
        self.assertIn(f"真太阳时约 {m['pillar_time']['time']}", md)
        self.assertIn("当前（虚岁35）处于 35–44岁", md)
        for section in ["## 基本信息", "## 时辰说明", "## 置信度", "### 四柱八字", "### 袁天罡称骨",
                        "### 紫微斗数", "#### 六宫深度解读", "### 西洋星座", "### 三才五格",
                        "### 六维度倾向", "### 人格速写", "**和解命题**"]:
            self.assertIn(section, md)
        self.assertEqual(page.count("class='zc"), 13)
        self.assertIn("type='range'", page)

    def test_clock_comparison_appears_when_shichen_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "in.json"
            inp.write_text(json.dumps({"members": [{
                "name": "测试", "name_is_alias": True, "gender": "男", "solar_date": "1996-08-20",
                "birth_time": "15:30", "birth_city": "景洪", "birth_lat": 22.01, "birth_lon": 100.80}]},
                ensure_ascii=False), encoding="utf-8")
            nar = load_example()
            nar["persons"] = [person_narrative("测试")]
            nar["persons"][0].pop("wuge_reading")
            nf = Path(tmp) / "n.json"
            nf.write_text(json.dumps(nar, ensure_ascii=False), encoding="utf-8")
            paths = run_pipeline(inp, Path(tmp) / "out", narrative_path=nf, as_of_year=2026)
            md = paths["final_md"].read_text(encoding="utf-8")
        self.assertIn("| 时柱 | 辛未 | 壬申 |", md)
        self.assertIn("| 命宫 | 辛丑宫 借", md)
        self.assertIn("庚子宫 紫微", md)
        self.assertNotIn("### 三才五格", md)


class RelationAndValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a = analyze_person({"name": "甲", "name_is_alias": True, "gender": "男", "solar_date": "1990-06-06",
                            "birth_time": "10:00", "birth_lat": 39.9, "birth_lon": 116.4})
        b = analyze_person({"name": "乙", "name_is_alias": True, "gender": "女", "solar_date": "1990-09-09",
                            "birth_time": "10:00", "birth_lat": 31.2, "birth_lon": 121.5})
        cls.chart = {"members": [a, b], "synastry": analyze_synastry([a, b])}

    def narrative(self, rel):
        nar = load_example()
        nar["persons"] = [person_narrative("甲"), person_narrative("乙")]
        for p in nar["persons"]:
            p.pop("wuge_reading")
        nar["relation"] = rel
        return nar

    def test_synastry_scores_come_from_chart(self):
        T = {"adv": "a", "risk": "r", "act": "c"}
        rel = {"type": "synastry", "reading": [T], "nourish": "n", "drain": "d", "window": "w",
               "advice": [["工作", "x"]], "reconciliation": "与差异和解——不是消除差异，而是分工。"}
        md, page = render(self.chart, self.narrative(rel), 2026)
        self.assertIn(f"| **合计** | **{self.chart['synastry']['score']}** |", md)
        self.assertIn("午", self.chart["members"][0]["bazi"][0])
        self.assertIn("同支比和、自刑", md)
        self.assertIn("合盘总览", page)

    def test_parent_child_section(self):
        rel = {"type": "parent_child", "title": "亲子关系", "kid_core": "k", "match": [["日主", "x"]],
               "nourish": "n", "suppress": "s", "advice": [["学习", "y"]],
               "reconciliation": "与期待和解——不是放弃要求，而是看见孩子。"}
        md, _ = render({"members": self.chart["members"], "synastry": None}, self.narrative(rel), 2026)
        self.assertIn("## 3. 亲子关系", md)

    def test_rejects_name_mismatch_and_bad_reconciliation(self):
        nar = self.narrative(None)
        nar.pop("relation")
        nar["persons"][1]["name"] = "丙"
        with self.assertRaises(ReportError):
            render(self.chart, nar, 2026)
        nar["persons"][1]["name"] = "乙"
        nar["persons"][1]["sketch"]["reconciliation"] = "好好生活。"
        with self.assertRaises(ReportError):
            render(self.chart, nar, 2026)

    def test_html_escapes_narrative(self):
        nar = self.narrative(None)
        nar.pop("relation")
        nar["persons"][0]["advice"][0] = "<script>alert(1)</script>"
        _, page = render(self.chart, nar, 2026)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)


class ReviewRegressionTests(unittest.TestCase):
    def setUp(self):
        self.nar = load_example()

    def chart_for(self, **member):
        base = {"name": "陈明远", "gender": "男", "solar_date": "1992-03-15", "birth_time": "14:30",
                "birth_lat": 30.59, "birth_lon": 114.31}
        base.update(member)
        return {"members": [analyze_person(base)], "synastry": None}

    def test_schema_violation_is_rejected(self):
        self.nar["persons"][0]["six_dimensions"]["career"]["signals"]["bazi"][0] = 150
        with self.assertRaises(ReportError):
            render(self.chart_for(mbti="INTJ"), self.nar, 2026)

    def test_wuge_facts_render_without_reading(self):
        self.nar["persons"][0].pop("wuge_reading")
        md, _ = render(self.chart_for(mbti="INTJ"), self.nar, 2026)
        self.assertIn("### 三才五格", md)
        self.assertIn("综合评分", md)

    def test_explicit_clock_basis_is_not_described_as_missing_data(self):
        md, _ = render(self.chart_for(mbti="INTJ", time_basis="clock"), self.nar, 2026)
        self.assertIn("按用户指定的钟表时间", md)
        self.assertNotIn("未取得出生地坐标", md)

    def test_utc9_outside_china_is_not_called_china_dst(self):
        md, _ = render(self.chart_for(mbti="INTJ", birth_lat=37.57, birth_lon=126.98), self.nar, 2026)
        self.assertNotIn("夏令时", md.split("## 置信度")[0])

    def test_current_dayun_after_sixth_limit_is_listed(self):
        chart = self.chart_for(mbti="INTJ")
        md, page = render(chart, self.nar, 2072)
        cur = [d for d in chart["members"][0]["ziwei"]["大限序列"] if d["年龄范围"] in md.split("当前（虚岁81）处于 ")[1][:12]]
        self.assertTrue(cur)
        self.assertIn(f"{cur[0]['年龄范围']} {cur[0]['宫位']}", md)
        self.assertIn("tli cur", page)

    def test_slider_disables_initial_animation(self):
        _, page = render(self.chart_for(mbti="INTJ"), self.nar, 2026)
        self.assertIn("style.animation='none'", page)


class AliasSynastryTests(unittest.TestCase):
    def test_name_band_hidden_when_not_applicable(self):
        members = [analyze_person({"name": n, "name_is_alias": True, "gender": "男", "solar_date": d,
                                   "birth_time": "10:00", "birth_lat": 39.9, "birth_lon": 116.4})
                   for n, d in [("甲", "1991-02-10"), ("乙", "1993-07-07")]]
        chart = {"members": members, "synastry": analyze_synastry(members)}
        self.assertEqual(chart["synastry"]["max_possible"], 95)
        nar = load_example()
        nar["persons"] = [person_narrative("甲"), person_narrative("乙")]
        for p in nar["persons"]:
            p.pop("wuge_reading")
        T = {"adv": "a", "risk": "r", "act": "c"}
        nar["relation"] = {"type": "synastry", "reading": [T], "nourish": "n", "drain": "d", "window": "w",
                           "advice": [["工作", "x"]], "reconciliation": "与差异和解——不是消除差异，而是分工。"}
        md, page = render(chart, nar, 2026)
        self.assertNotIn("| 姓名合盘 |", md)
        self.assertNotIn("<span>姓名合盘</span>", page)
        from render_report import synastry_rows
        rows = synastry_rows(chart["synastry"])
        self.assertEqual(sum(r[2] for r in rows), chart["synastry"]["max_possible"])
        for label, score, cap, _ in rows:
            self.assertIn(f"| {label} | {score} | {cap} |", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
