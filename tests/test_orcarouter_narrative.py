#!/usr/bin/env python3
"""OrcaRouter 脱敏、字段白名单与响应解析回归测试。"""

from __future__ import annotations

import copy
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from orcarouter_narrative import (  # noqa: E402
    _parse_json_content,
    apply_narrative,
    build_anonymized_context,
    enhance_file,
)
from tianji import run_pipeline  # noqa: E402


NARRATIVE = {
    "core_resonance_description": "成员之间存在互补线索，但需要由实际协作验证。可以用一次复盘确认各自优势是否真的发挥。",
    "will_synergy_description": "目标节奏并不完全相同。先明确共同目标，再允许成员采用不同实现路径。",
    "outer_friction_description": "摩擦更适合作为待观察假设。遇到分歧时记录事实、影响和请求，避免给人贴标签。",
    "overall_comment": "这份结果只是一组民俗观察线索，不代表固定的人格或未来。团队有可利用的互补，也有需要显性协调的节奏差异。建议先以短周期任务验证分工，再根据实际结果调整角色。重要的人事与财务决定应以能力、绩效和专业判断为准。",
    "scenario_advice": "为 P1、P2、P3 设定清晰的责任边界和交付标准。每周复盘一次真实行为，只保留被事实支持的观察。",
    "compatibility_summary_line": "以现实协作为准，让差异成为可验证的互补。",
}


class OrcaRouterNarrativeTests(unittest.TestCase):
    def _reading(self, tmp: str) -> dict:
        paths = run_pipeline(
            ROOT / "tests" / "fixtures" / "input_three_people.json",
            Path(tmp),
            scenario="团队协作",
        )
        return json.loads(paths["reading"].read_text(encoding="utf-8"))

    def test_context_excludes_direct_identifiers_and_birth_pillars(self):
        with tempfile.TemporaryDirectory() as tmp:
            reading = self._reading(tmp)
            context = build_anonymized_context(reading)
            serialized = json.dumps(context, ensure_ascii=False)
            for forbidden in (
                "甲方", "乙方", "丙方", "1990-05-20", "1992-08-16",
                "北京", "上海", "成都", "male", "female", "pillars",
            ):
                self.assertNotIn(forbidden, serialized)
            self.assertEqual([m["id"] for m in context["members"]], ["P1", "P2", "P3"])

    def test_apply_narrative_cannot_change_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            reading = self._reading(tmp)
            scores_before = copy.deepcopy(reading["synastry"]["composite_scores"])
            enhanced = apply_narrative(reading, NARRATIVE, model="orcarouter/free")
            self.assertEqual(scores_before, enhanced["synastry"]["composite_scores"])
            self.assertEqual(
                enhanced["synastry"]["overall_comment"], NARRATIVE["overall_comment"]
            )
            self.assertIn("脱敏计算摘要", enhanced["meta"]["notes"])

    def test_parser_accepts_json_fence(self):
        parsed = _parse_json_content("```json\n" + json.dumps(NARRATIVE, ensure_ascii=False) + "\n```")
        self.assertEqual(parsed, NARRATIVE)

    def test_parser_extracts_json_after_reasoning_or_prefix(self):
        content = (
            "<think>先分析，但这一段不应进入结果。</think>\n"
            "以下是 JSON：\n" + json.dumps(NARRATIVE, ensure_ascii=False) + "\n完成"
        )
        self.assertEqual(_parse_json_content(content), NARRATIVE)

    def test_missing_secret_preserves_offline_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            reading = self._reading(tmp)
            source = Path(tmp) / "reading.json"
            output = Path(tmp) / "fallback.json"
            with contextlib.redirect_stdout(io.StringIO()):
                used_model = enhance_file(
                    source, output, api_key=None, model="orcarouter/free"
                )
            self.assertFalse(used_model)
            self.assertEqual(reading, json.loads(output.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
