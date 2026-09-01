#!/usr/bin/env python3
"""天机输入与 reading.json 契约的唯一验证入口。"""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover - 由 CLI 给出可操作错误
    raise RuntimeError("缺少 jsonschema；请运行 pip install -r requirements.txt") from exc


ROOT = Path(__file__).resolve().parent.parent
READING_SCHEMA_PATH = ROOT / "schemas" / "reading_v8.schema.json"
INPUT_SCHEMA_PATH = ROOT / "schemas" / "input_v1.schema.json"
SCHEMA_VERSION = "8.3"
ENGINE_VERSION = "8.3.0"


class ContractError(ValueError):
    """输入或输出不符合天机数据契约。"""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_errors(errors: list[jsonschema.ValidationError]) -> str:
    lines = []
    for error in errors[:12]:
        path = ".".join(str(p) for p in error.absolute_path) or "<root>"
        lines.append(f"{path}: {error.message}")
    if len(errors) > 12:
        lines.append(f"另有 {len(errors) - 12} 项错误")
    return "\n".join(lines)


def normalize_reading(data: dict[str, Any]) -> dict[str, Any]:
    """兼容早期文档中的字段别名，并统一升级到当前契约版本。"""
    normalized = copy.deepcopy(data)
    meta = normalized.setdefault("meta", {})
    if "scene" not in meta and "mode" in meta:
        meta["scene"] = meta.pop("mode")
    if meta.get("version") in {None, "8.0", "8.1", "8.2"}:
        meta["version"] = SCHEMA_VERSION

    aliases = {
        "western": "western_astro",
        "name_wuge": "name_analysis",
        "sketch": "personality_sketch",
        "confidence": "confidence_table",
    }
    for person in normalized.get("persons", []):
        for old, new in aliases.items():
            if new not in person and old in person:
                person[new] = person.pop(old)
    return normalized


def validate_reading(data: dict[str, Any], *, normalize: bool = False) -> dict[str, Any]:
    candidate = normalize_reading(data) if normalize else data
    validator = jsonschema.Draft202012Validator(_load_json(READING_SCHEMA_PATH))
    errors = sorted(
        validator.iter_errors(candidate),
        key=lambda e: tuple(str(part) for part in e.absolute_path),
    )
    if errors:
        raise ContractError("reading.json 不符合契约：\n" + _format_errors(errors))

    persons = candidate["persons"]
    indexes = [person["person_index"] for person in persons]
    expected_indexes = list(range(1, len(persons) + 1))
    if indexes != expected_indexes:
        raise ContractError(
            f"reading.json 不符合契约：person_index 必须连续且从 1 开始；"
            f"当前为 {indexes}"
        )

    scene = candidate["meta"]["scene"]
    synastry = candidate.get("synastry")
    if scene == "personal" and (len(persons) != 1 or synastry is not None):
        raise ContractError("reading.json 不符合契约：personal 必须恰好 1 人且 synastry 为 null/省略")
    if scene == "synastry" and (len(persons) < 2 or not isinstance(synastry, dict)):
        raise ContractError("reading.json 不符合契约：synastry 必须至少 2 人并提供合盘对象")
    return candidate


def validate_input(data: dict[str, Any]) -> dict[str, Any]:
    validator = jsonschema.Draft202012Validator(_load_json(INPUT_SCHEMA_PATH))
    errors = sorted(
        validator.iter_errors(data),
        key=lambda e: tuple(str(part) for part in e.absolute_path),
    )
    if errors:
        raise ContractError("输入 JSON 不符合契约：\n" + _format_errors(errors))

    for index, member in enumerate(data["members"], start=1):
        try:
            datetime.strptime(member["solar_date"], "%Y-%m-%d")
        except ValueError as exc:
            raise ContractError(f"members.{index - 1}.solar_date: 不是有效公历日期") from exc
    return data


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="验证或规范化天机 JSON 契约")
    parser.add_argument("path", help="要验证的 JSON 文件")
    parser.add_argument("--kind", choices=["input", "reading"], default="reading")
    parser.add_argument("--normalize", action="store_true", help="兼容旧字段并升级后原地写回")
    args = parser.parse_args()

    path = Path(args.path)
    data = _load_json(path)
    if args.kind == "input":
        validate_input(data)
    else:
        data = validate_reading(data, normalize=args.normalize)
        if args.normalize:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[天机] 契约验证通过：{path}")


if __name__ == "__main__":
    main()
