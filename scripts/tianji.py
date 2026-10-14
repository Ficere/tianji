#!/usr/bin/env python3
"""天机 v8.5 一站式流水线：输入校验 → 排盘 → reading → HTML；可输出编辑式 Markdown/HTML/PDF。"""

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
    report_style: str = "legacy",
    pdf: bool = False,
) -> dict[str, Path]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    validate_input(data)

    members = [analyze_person(member) for member in data["members"]]
    for raw, result in zip(data["members"], members):
        for key in ("birth_time_source", "birth_time_note"):
            if key in raw:
                result[key] = raw[key]
        if raw.get("birth_time_source") == "assumed":
            result.setdefault("warnings", []).append({
                "code": "BIRTH_TIME_ASSUMED",
                "message": f"用户指定 {raw['birth_time']} 为假设时刻，真实出生时辰未知；{raw['birth_time_note']}",
            })
        result["clock_alternative"] = clock_alternative(raw, result)
    synastry = analyze_synastry(members) if len(members) > 1 else None
    chart = {
        "members": members,
        "synastry": synastry,
        "version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
    }
    reading = build_reading(chart, title=title, scenario=scenario)
    assumed = [m for m in members if m.get("birth_time_source") == "assumed"]
    if assumed:
        reading["meta"]["notes"] = "；".join(
            f"{m['name']} {m['birth_time']} 为用户指定假设时刻，实际时辰未知；{m['birth_time_note']}"
            for m in assumed) + "。完整输出是条件结果，不是已核实的出生盘。"
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
        if report_style == "editorial":
            from editorial_report import render as render_editorial
            md, page = render_editorial(chart, narrative, as_of_year)
        elif report_style == "legacy":
            md, page = render_report(chart, narrative, as_of_year)
        else:
            raise ValueError(f"未知 report_style: {report_style}")
        paths["final_md"] = output_dir / "tianji_report.md"
        paths["final_html"] = output_dir / "tianji_report.html"
        paths["final_md"].write_text(md, encoding="utf-8")
        paths["final_html"].write_text(page, encoding="utf-8")
        if pdf:
            if report_style != "editorial":
                raise ValueError("--pdf 仅支持 editorial 格式")
            from editorial_report import write_pdf
            paths["final_pdf"] = output_dir / "tianji_report.pdf"
            write_pdf(page, paths["final_pdf"])
    elif pdf:
        raise ValueError("--pdf 需要 --narrative，不可把快速预览当最终报告")
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
    parser = argparse.ArgumentParser(description="天机 v8.5 一站式报告生成器")
    parser.add_argument("--input", required=True, type=Path, help="符合 input_v1 的 JSON")
    parser.add_argument("--output-dir", type=Path, default=Path("tianji-output"))
    parser.add_argument("--title")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--narrative", type=Path, help="Agent 撰写的 narrative_v1 JSON；提供时输出固定格式 tianji_report.md/.html")
    parser.add_argument("--as-of-year", type=int, help="计算当前大限所用年份，默认今年")
    parser.add_argument("--report-style", choices=("editorial", "legacy"), default="editorial",
                        help="最终报告格式；CLI 默认 editorial，legacy 保留旧版")
    parser.add_argument("--pdf", action="store_true", help="同时生成编辑式 PDF（需 requirements-report.txt）")
    args = parser.parse_args()

    paths = run_pipeline(
        args.input, args.output_dir, title=args.title, scenario=args.scenario,
        narrative_path=args.narrative, as_of_year=args.as_of_year,
        report_style=args.report_style, pdf=args.pdf,
    )
    print("[天机] 流水线完成")
    for kind, path in paths.items():
        print(f"  {kind}: {path}")


if __name__ == "__main__":
    main()
