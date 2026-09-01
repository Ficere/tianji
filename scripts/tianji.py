#!/usr/bin/env python3
"""天机 v8.3 一站式流水线：输入校验 → 排盘 → reading → HTML。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_reading import SCENARIOS, build_reading
from fortune_calc import analyze_person, analyze_synastry
from generate_html import render_html
from reading_contract import ENGINE_VERSION, SCHEMA_VERSION, validate_input


def run_pipeline(
    input_path: Path,
    output_dir: Path,
    *,
    title: str | None = None,
    scenario: str | None = None,
) -> dict[str, Path]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    validate_input(data)

    members = [analyze_person(member) for member in data["members"]]
    synastry = analyze_synastry(members) if len(members) > 1 else None
    chart = {
        "members": members,
        "synastry": synastry,
        "version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
    }
    reading = build_reading(chart, title=title, scenario=scenario)
    report = render_html(reading)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "chart": output_dir / "chart.json",
        "reading": output_dir / "reading.json",
        "report": output_dir / "report.html",
    }
    paths["chart"].write_text(
        json.dumps(chart, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["reading"].write_text(
        json.dumps(reading, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["report"].write_text(report, encoding="utf-8")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="天机 v8.3 一站式报告生成器")
    parser.add_argument("--input", required=True, type=Path, help="符合 input_v1 的 JSON")
    parser.add_argument("--output-dir", type=Path, default=Path("tianji-output"))
    parser.add_argument("--title")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS))
    args = parser.parse_args()

    paths = run_pipeline(
        args.input, args.output_dir, title=args.title, scenario=args.scenario
    )
    print("[天机] 流水线完成")
    for kind, path in paths.items():
        print(f"  {kind}: {path}")


if __name__ == "__main__":
    main()
