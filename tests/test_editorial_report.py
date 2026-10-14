"""编辑式结构、假设输入、安全渲染与 PDF 回归；全部使用虚构资料。"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from editorial_report import MARRIAGE_TOPICS, render
from reading_contract import ContractError, validate_input
from render_report import ReportError, render as render_legacy
from tianji import run_pipeline


def input_data():
    return {"members": [
        {"name": "示例甲", "name_is_alias": True, "gender": "女",
         "solar_date": "1994-06-12", "birth_time": "09:30",
         "birth_city": "上海市", "birth_lat": 31.23, "birth_lon": 121.47},
        {"name": "示例乙", "name_is_alias": True, "gender": "男",
         "solar_date": "1991-12-03", "birth_time": "12:00",
         "birth_city": "成都市", "birth_lat": 30.67, "birth_lon": 104.06,
         "birth_time_source": "assumed",
         "birth_time_note": "虚构测试：用户指定中午假设，实际时辰未知"}]}


def narrative(chart):
    old = json.loads((ROOT / "examples/report/example_narrative.json").read_text(encoding="utf-8"))
    persons = []
    for member in chart["members"]:
        p = copy.deepcopy(old["persons"][0])
        p["name"] = member["name"]
        p.pop("wuge_reading", None)
        p.pop("mbti_note", None)
        p.pop("six_dimensions", None)
        p["strength"] = member["deep"]["day_master"]["标签"]
        p["favor"] = member["deep"]["yongshen"]["用神"] or "以脚本通关规则观察"
        persons.append(p)
    t = {"adv": "用实际经历核对", "risk": "不可把符号当现实事件", "act": "一次只验证一个行为"}
    return {
        "title": "虚构伴侣 · 婚前合盘", "scenario": "情侣/伴侣",
        "persons": persons, "confidence": [["时辰", "条件结果", "一人中午是假设"]],
        "footer": {"confidence_pct": None, "factors": "输入与预测效度分开", "questions": "核对真实时辰和行为"},
        "relation": {"type": "synastry", "reading": [t], "nourish": "可核对支持方式",
                     "drain": "可核对责任边界", "window": "按实际条件安排，不据流年择婚期",
                     "advice": [["沟通", "约定一周现实验证"]],
                     "reconciliation": "与差异和解——不是消除差异，而是说清需要。"},
        "editorial": {"subtitle": "不替对方决定", "stage": "准备结婚",
                      "cooperation_title": "婚前共同生活与协作",
                      "cooperation_sections": [{"title": title, "text": "双方讨论并留记录"} for title in MARRIAGE_TOPICS],
                      "coordinate_sources": []},
    }


class EditorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text(json.dumps(input_data(), ensure_ascii=False), encoding="utf-8")
            result = run_pipeline(path, Path(tmp) / "out")
            cls.chart = json.loads(result["chart"].read_text(encoding="utf-8"))

    def test_section_order_and_complete_fact_modules(self):
        nar = narrative(self.chart)
        md, page = render(self.chart, nar, 2026)
        headings = ["## 基础信息与置信度", "## 个人命盘", "## 伴侣合盘",
                    "## 婚前共同生活与协作", "## 当前阶段与时间线", "## 和解命题与校准", "## 附录"]
        self.assertEqual(sorted(md.index(s) for s in headings), [md.index(s) for s in headings])
        for member in self.chart["members"]:
            self.assertIn(" · ".join(member["bazi"]), md)
            self.assertIn(member["chenggu"]["歌诀"], md)
        self.assertIn("四化：", md)
        self.assertIn("藏干／十神：", md)
        self.assertIn("未来三年", md)
        self.assertNotIn("type='range'", page)
        self.assertNotIn("六维度倾向", md)
        self.assertNotIn("置信度约", md)
        self.assertIn("<blockquote>", page)
        self.assertIn("真太阳时", md)

    def test_assumptions_survive_chart_and_render(self):
        member = self.chart["members"][1]
        self.assertEqual(member["birth_time_source"], "assumed")
        self.assertIn("BIRTH_TIME_ASSUMED", [w["code"] for w in member["warnings"]])
        md, page = render(self.chart, narrative(self.chart), 2026)
        self.assertIn("示例乙【假设盘】", md)
        self.assertIn("12:00【假设】", md)
        self.assertIn("真实出生时辰未知", md)
        self.assertIn("data-label='示例乙 12:00 假设'", page)
        self.assertIn("不是成功概率", md)

    def test_schema_requires_note_for_assumed_time(self):
        data = input_data()
        del data["members"][1]["birth_time_note"]
        with self.assertRaises(ContractError):
            validate_input(data)

    def test_schema_rejects_invented_source(self):
        data = input_data()
        data["members"][1]["birth_time_source"] = "auto-guessed"
        with self.assertRaises(ContractError):
            validate_input(data)

    def test_schema_does_not_require_note_for_recorded_time(self):
        data = input_data()
        data["members"][1]["birth_time_source"] = "recorded"
        del data["members"][1]["birth_time_note"]
        validate_input(data)

    def test_missing_assumed_note_in_chart_is_rejected(self):
        chart = copy.deepcopy(self.chart)
        del chart["members"][1]["birth_time_note"]
        with self.assertRaises(ReportError):
            render(chart, narrative(chart), 2026)

    def test_marriage_missing_topic_is_rejected(self):
        nar = narrative(self.chart)
        nar["editorial"]["cooperation_sections"].pop()
        with self.assertRaises(ReportError):
            render(self.chart, nar, 2026)

    def test_non_marriage_does_not_force_marriage_topics(self):
        nar = narrative(self.chart)
        nar["editorial"] = {"stage": "朋友"}
        render(self.chart, nar, 2026)

    def test_null_confidence_and_no_six_scores_are_supported(self):
        md, _ = render(self.chart, narrative(self.chart))
        self.assertNotIn("None%", md)
        self.assertIn("不提供总体预测置信度百分比", md)

    def test_legacy_cannot_hide_assumed_time(self):
        with self.assertRaises(ReportError):
            render_legacy(self.chart, narrative(self.chart), 2026)

    def test_xss_and_unsafe_links_are_not_executed(self):
        nar = narrative(self.chart)
        nar["editorial"]["subtitle"] = "<script>alert(1)</script>"
        nar["persons"][0]["advice"][0] = '<img src=x onerror=alert(1)> [坏地址](javascript:alert)'
        _, page = render(self.chart, nar)
        self.assertNotIn("<script>", page)
        self.assertNotIn("<img src=x", page)
        self.assertNotIn('href="javascript:', page)
        self.assertIn("&lt;script&gt;", page)

    def test_coordinates_require_http_and_survive_pdf_html(self):
        nar = narrative(self.chart)
        nar["editorial"]["coordinate_sources"] = [
            {"name": "示例甲", "note": "区县代表点", "url": "https://example.org/coordinates"}]
        md, page = render(self.chart, nar)
        self.assertIn("https://example.org/coordinates", md)
        self.assertIn('href="https://example.org/coordinates"', page)
        nar["editorial"]["coordinate_sources"][0]["url"] = "file:///etc/passwd"
        with self.assertRaises(ReportError):
            render(self.chart, nar)

    def test_totals_match_chart_and_denominator(self):
        syn = self.chart["synastry"]
        md, _ = render(self.chart, narrative(self.chart))
        self.assertIn(f"{syn['score']}／{syn['max_possible']}", md)
        self.assertNotIn("姓名合盘 |", md)

    def test_cli_defaults_to_editorial_and_pdf_end_to_end(self):
        try:
            import weasyprint
        except ImportError:
            self.skipTest("安装 requirements-report.txt 才运行 PDF 集成")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ip, np = tmp / "input.json", tmp / "narrative.json"
            ip.write_text(json.dumps(input_data(), ensure_ascii=False), encoding="utf-8")
            np.write_text(json.dumps(narrative(self.chart), ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/tianji.py"),
                                     "--input", str(ip), "--narrative", str(np),
                                     "--output-dir", str(tmp / "out"), "--pdf", "--as-of-year", "2026"],
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            md = (tmp / "out/tianji_report.md").read_text(encoding="utf-8")
            self.assertIn("## 基础信息与置信度", md)
            self.assertTrue((tmp / "out/tianji_report.pdf").read_bytes().startswith(b"%PDF"))
            self.assertGreater((tmp / "out/tianji_report.pdf").stat().st_size, 10000)

    def test_pdf_requires_narrative(self):
        with tempfile.TemporaryDirectory() as tmp:
            ip = Path(tmp) / "input.json"
            ip.write_text(json.dumps(input_data(), ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                run_pipeline(ip, Path(tmp) / "out", report_style="editorial", pdf=True)

    def test_single_person_does_not_invent_synastry(self):
        chart = copy.deepcopy(self.chart)
        chart["members"] = chart["members"][:1]
        chart["synastry"] = None
        nar = narrative(chart)
        nar.pop("relation")
        nar["editorial"] = {}
        nar["scenario"] = "个人"
        md, _ = render(chart, nar)
        self.assertNotIn("## 伴侣合盘", md)
        self.assertIn("## 个人命盘", md)

    def test_parent_child_keeps_its_own_scene(self):
        nar = narrative(self.chart)
        nar["scenario"] = "亲子"
        nar["editorial"] = {"cooperation_title": "亲子顺势养育"}
        nar["relation"] = {"type": "parent_child", "title": "亲子关系", "kid_core": "观察与验证",
                           "match": [["节奏", "核对真实需要"]], "nourish": "共同表达", "suppress": "避免安排过多",
                           "advice": [["亲子", "尊重选择"]], "reconciliation": "与期待和解——不是取消边界，而是一起商量。"}
        md, _ = render(self.chart, nar)
        self.assertIn("## 家庭合盘", md)
        self.assertIn("## 亲子顺势养育", md)
        self.assertNotIn("## 婚前共同生活", md)

    def test_eight_people_map_uses_three_columns_not_ten(self):
        from fortune_calc import analyze_person, analyze_synastry
        members = [analyze_person({**input_data()["members"][0], "name": f"虚构{i+1}"}) for i in range(8)]
        chart = {"members": members, "synastry": analyze_synastry(members)}
        nar = narrative(chart)
        nar["scenario"] = "团队协作"
        nar["editorial"] = {"cooperation_title": "团队协作指南"}
        md, page = render(chart, nar)
        self.assertIn("| 五行 | 各成员表层统计 | 合计 |", md)
        self.assertIn("虚构8", page)


if __name__ == "__main__":
    unittest.main()
