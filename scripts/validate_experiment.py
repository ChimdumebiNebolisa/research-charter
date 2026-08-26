#!/usr/bin/env python3
"""Validate experiment records without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "problems" / "PROBLEM_REGISTRY.json"
SCHEMA_PATH = ROOT / "schemas" / "experiment.schema.json"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - message is the useful part
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def type_matches(value: Any, expected: str | list[str]) -> bool:
    expected_types = [expected] if isinstance(expected, str) else expected
    for kind in expected_types:
        if kind == "null" and value is None:
            return True
        if kind == "object" and isinstance(value, dict):
            return True
        if kind == "array" and isinstance(value, list):
            return True
        if kind == "string" and isinstance(value, str):
            return True
        if kind == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if kind == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if kind == "boolean" and isinstance(value, bool):
            return True
    return False


def validate_schema(record: dict[str, Any], schema: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    for key in schema.get("required", []):
        if key not in record:
            errors.append(f"{path}: missing required field {key!r}")
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        unknown = sorted(set(record) - set(properties))
        errors.extend(f"{path}: unknown field {key!r}" for key in unknown)
    for key, rule in properties.items():
        if key not in record:
            continue
        value = record[key]
        if "const" in rule and value != rule["const"]:
            errors.append(f"{path}: {key} must equal {rule['const']!r}")
        if "type" in rule and not type_matches(value, rule["type"]):
            errors.append(f"{path}: {key} has wrong type")
            continue
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"{path}: {key} must be one of {rule['enum']!r}")
        if isinstance(value, str):
            if len(value) < rule.get("minLength", 0):
                errors.append(f"{path}: {key} is too short")
            if "pattern" in rule and re.fullmatch(rule["pattern"], value) is None:
                errors.append(f"{path}: {key} does not match its required pattern")
            if rule.get("format") == "date-time":
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    errors.append(f"{path}: {key} is not an ISO-8601 date-time")
        if isinstance(value, list):
            if len(value) < rule.get("minItems", 0):
                errors.append(f"{path}: {key} has too few items")
            item_rule = rule.get("items", {})
            for index, item in enumerate(value):
                if "type" in item_rule and not type_matches(item, item_rule["type"]):
                    errors.append(f"{path}: {key}[{index}] has wrong type")
        if isinstance(value, dict):
            if len(value) < rule.get("minProperties", 0):
                errors.append(f"{path}: {key} has too few properties")
    return errors


def records_at(path: Path) -> list[tuple[Path, dict[str, Any]]]:
    paths = [path] if path.is_file() else sorted(path.rglob("*.json"))
    records: list[tuple[Path, dict[str, Any]]] = []
    for record_path in paths:
        try:
            record = load_json(record_path)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if not isinstance(record, dict):
            raise ValueError(f"{record_path}: record must be a JSON object")
        records.append((record_path, record))
    return records


def registry_targets() -> tuple[set[str], dict[str, str]]:
    registry = load_json(REGISTRY_PATH)
    problems = registry.get("problems", [])
    allowed = set(registry.get("allowed_problem_ids", []))
    targets = {item["problem_id"]: item["target_id"] for item in problems}
    if allowed != set(targets):
        raise ValueError("problem registry allowed_problem_ids and problems disagree")
    return allowed, targets


def validate(path: Path) -> list[str]:
    allowed, targets = registry_targets()
    schema = load_json(SCHEMA_PATH)
    errors: list[str] = []
    experiment_ids: set[str] = set()
    for record_path, record in records_at(path):
        record_type = record.get("record_type")
        if record_type == "candidate":
            continue
        if record_type != "experiment":
            errors.append(f"{record_path}: unknown record_type {record_type!r}")
            continue
        errors.extend(validate_schema(record, schema, record_path))
        problem_id = record.get("problem_id")
        target_id = record.get("target_id")
        if problem_id not in allowed:
            errors.append(f"{record_path}: problem_id is not frozen: {problem_id!r}")
        elif target_id != targets[problem_id]:
            errors.append(f"{record_path}: target_id does not match frozen target for {problem_id}")
        commit = record.get("git_commit_sha")
        if isinstance(commit, str) and SHA_RE.fullmatch(commit) is None:
            errors.append(f"{record_path}: git_commit_sha is not a full hexadecimal SHA")
        experiment_id = record.get("experiment_id")
        if isinstance(experiment_id, str):
            if experiment_id in experiment_ids:
                errors.append(f"{record_path}: duplicate experiment_id {experiment_id!r}")
            experiment_ids.add(experiment_id)
        parents = record.get("parent_experiment_ids", [])
        if isinstance(parents, list) and len(parents) != len(set(parents)):
            errors.append(f"{record_path}: parent_experiment_ids contains duplicates")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=ROOT / "experiments")
    args = parser.parse_args()
    try:
        errors = validate(args.path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"experiment validation passed: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
