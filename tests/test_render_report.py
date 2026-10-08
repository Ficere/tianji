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

EXAMPLE_INPUT = ROOT / "examples" / "report" / "example_report_input.json"
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
