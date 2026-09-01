#!/usr/bin/env python3
"""Contract, security, and multi-person end-to-end regression tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from generate_html import render_html  # noqa: E402
from reading_contract import ContractError, validate_input, validate_reading  # noqa: E402
from tianji import run_pipeline  # noqa: E402


class InputContractTests(unittest.TestCase):
    def test_rejects_invalid_time_and_calendar_date(self):
        base = {
            "members": [{
                "name": "甲方", "gender": "男",
                "solar_date": "2024-02-30", "birth_time": "25:00",
            }]
        }
        with self.assertRaises(ContractError):
            validate_input(base)

    def test_rejects_unknown_fields(self):
        bad = {
            "members": [{
                "name": "甲方", "gender": "男",
                "solar_date": "2024-02-10", "birth_time": "09:00",
                "secret": "should-not-pass",
            }]
        }
        with self.assertRaises(ContractError):
            validate_input(bad)


class PipelineTests(unittest.TestCase):
    def test_three_person_pipeline_produces_valid_artifacts(self):
        fixture = ROOT / "tests" / "fixtures" / "input_three_people.json"
        with tempfile.TemporaryDirectory() as tmp:
            paths = run_pipeline(
                fixture, Path(tmp), title="三人团队报告", scenario="团队协作"
            )
            self.assertEqual(set(paths), {"chart", "reading", "report"})
            for path in paths.values():
                self.assertTrue(path.exists())

            chart = json.loads(paths["chart"].read_text(encoding="utf-8"))
            self.assertTrue(all(person["wuge"] is None for person in chart["members"]))
            self.assertEqual(chart["synastry"]["max_possible"], 95)

            reading = json.loads(paths["reading"].read_text(encoding="utf-8"))
            validate_reading(reading)
            self.assertEqual(reading["meta"]["version"], "8.3")
            self.assertEqual(reading["meta"]["engine_version"], "8.3.0")
            self.assertEqual(len(reading["persons"]), 3)
            self.assertEqual(reading["synastry"]["scenario_advice"][0]["scenario"], "团队协作")
            self.assertGreater(paths["report"].stat().st_size, 50_000)

            broken = json.loads(paths["reading"].read_text(encoding="utf-8"))
            broken["persons"][1]["person_index"] = 8
            with self.assertRaises(ContractError):
                validate_reading(broken)

    def test_html_escapes_untrusted_strings(self):
        fixture = ROOT / "tests" / "fixtures" / "input_three_people.json"
        with tempfile.TemporaryDirectory() as tmp:
            paths = run_pipeline(fixture, Path(tmp), scenario="团队协作")
            reading = json.loads(paths["reading"].read_text(encoding="utf-8"))
            payload = '<script>alert("x")</script>'
            reading["meta"]["title"] = payload
            reading["persons"][0]["name"] = payload
            html = render_html(reading)
            self.assertNotIn(payload, html)
            self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
