#!/usr/bin/env python3
"""Validate candidate records and their evidence labels."""

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
SCHEMA_PATH = ROOT / "schemas" / "candidate.schema.json"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
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
    return False


def validate_schema(record: dict[str, Any], schema: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    for key in schema.get("required", []):
        if key not in record:
            errors.append(f"{path}: missing required field {key!r}")
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        errors.extend(f"{path}: unknown field {key!r}" for key in sorted(set(record) - set(properties)))
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
        if isinstance(value, list) and len(value) < rule.get("minItems", 0):
            errors.append(f"{path}: {key} has too few items")
        if isinstance(value, dict) and len(value) < rule.get("minProperties", 0):
            errors.append(f"{path}: {key} has too few properties")
    return errors


def records_at(path: Path) -> list[tuple[Path, dict[str, Any]]]:
    paths = [path] if path.is_file() else sorted(path.rglob("*.json"))
    records: list[tuple[Path, dict[str, Any]]] = []
    for record_path in paths:
        record = load_json(record_path)
        if not isinstance(record, dict):
            raise ValueError(f"{record_path}: record must be a JSON object")
        records.append((record_path, record))
    return records


def validate(path: Path) -> list[str]:
    registry = load_json(REGISTRY_PATH)
    targets = {item["problem_id"]: item["target_id"] for item in registry["problems"]}
    schema = load_json(SCHEMA_PATH)
    records = records_at(path)
    experiment_ids = {record.get("experiment_id") for _, record in records if record.get("record_type") == "experiment"}
    errors: list[str] = []
    candidate_ids: set[str] = set()
    min_level = {
        "unverified": 0,
        "primary_evaluator": 2,
        "independently_reproduced": 3,
        "adversarially_verified": 4,
    }
    for record_path, record in records:
        if record.get("record_type") == "experiment":
            continue
        if record.get("record_type") != "candidate":
            errors.append(f"{record_path}: unknown record_type {record.get('record_type')!r}")
            continue
        errors.extend(validate_schema(record, schema, record_path))
        problem_id = record.get("problem_id")
        if problem_id not in targets:
            errors.append(f"{record_path}: problem_id is not frozen: {problem_id!r}")
        elif record.get("target_id") != targets[problem_id]:
            errors.append(f"{record_path}: target_id does not match frozen target for {problem_id}")
        commit = record.get("git_commit_sha")
        if isinstance(commit, str) and SHA_RE.fullmatch(commit) is None:
            errors.append(f"{record_path}: git_commit_sha is not a full hexadecimal SHA")
        candidate_id = record.get("candidate_id")
        if isinstance(candidate_id, str):
            if candidate_id in candidate_ids:
                errors.append(f"{record_path}: duplicate candidate_id {candidate_id!r}")
            candidate_ids.add(candidate_id)
        source = record.get("source_experiment_id")
        if isinstance(source, str) and not source.startswith("external:") and source not in experiment_ids:
            errors.append(f"{record_path}: source_experiment_id does not name a local experiment")
        status = record.get("validation_status")
        level = record.get("evidence_level")
        if status in min_level and isinstance(level, int) and level < min_level[status]:
            errors.append(f"{record_path}: validation_status {status!r} requires a higher evidence_level")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=ROOT / "experiments")
    args = parser.parse_args()
    try:
        errors = validate(args.path)
    except (ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"candidate validation passed: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
