#!/usr/bin/env python3
"""天机 v8.4 一站式流水线：输入校验 → 排盘 → reading → HTML；提供 narrative 时输出固定格式报告。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_reading import SCENARIOS, build_reading
from fortune_calc import analyze_person, analyze_synastry
from generate_html import render_html
from reading_contract import ENGINE_VERSION, SCHEMA_VERSION, validate_input
from render_report import MAJOR
from render_report import render as render_report


def run_pipeline(
    input_path: Path,
    output_dir: Path,
    *,
    title: str | None = None,
    scenario: str | None = None,
    narrative_path: Path | None = None,
    as_of_year: int | None = None,
) -> dict[str, Path]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    validate_input(data)

    members = [analyze_person(member) for member in data["members"]]
    for raw, result in zip(data["members"], members):
        result["clock_alternative"] = clock_alternative(raw, result)
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
    if narrative_path is not None:
        narrative = json.loads(Path(narrative_path).read_text(encoding="utf-8"))
        md, page = render_report(chart, narrative, as_of_year)
        paths["final_md"] = output_dir / "tianji_report.md"
        paths["final_html"] = output_dir / "tianji_report.html"
        paths["final_md"].write_text(md, encoding="utf-8")
        paths["final_html"].write_text(page, encoding="utf-8")
    return paths


def clock_alternative(raw: dict, result: dict) -> dict | None:
    """真太阳时与钟表时间落在不同时辰时，给出钟表直排的对照要点（仅供报告对照）。"""
    if (result.get("pillar_time") or {}).get("basis") != "true_solar":
        return None
    alt = analyze_person({**raw, "time_basis": "clock"})
    if alt["bazi"][3] == result["bazi"][3] and alt["ziwei"]["命宫"] == result["ziwei"]["命宫"]:
        return None
    ming = alt["ziwei"]["十二宫星曜"].get("命宫", [])
    major = [s for s in ming if s in MAJOR]
    return {
        "时柱": alt["bazi"][3],
        "命宫": alt["ziwei"]["命宫"],
        "命宫主星": "·".join(major) or "无主星",
        "身宫": alt["ziwei"]["身宫"],
        "称骨": alt["chenggu"]["总重"],
        "命宫星曜": ming,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="天机 v8.4 一站式报告生成器")
    parser.add_argument("--input", required=True, type=Path, help="符合 input_v1 的 JSON")
    parser.add_argument("--output-dir", type=Path, default=Path("tianji-output"))
    parser.add_argument("--title")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--narrative", type=Path, help="Agent 撰写的 narrative_v1 JSON；提供时输出固定格式 tianji_report.md/.html")
    parser.add_argument("--as-of-year", type=int, help="计算当前大限所用年份，默认今年")
    args = parser.parse_args()

    paths = run_pipeline(
        args.input, args.output_dir, title=args.title, scenario=args.scenario,
        narrative_path=args.narrative, as_of_year=args.as_of_year,
    )
    print("[天机] 流水线完成")
    for kind, path in paths.items():
        print(f"  {kind}: {path}")


if __name__ == "__main__":
    main()
