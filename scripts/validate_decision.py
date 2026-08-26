#!/usr/bin/env python3
"""Validate the append-only research director decision log."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "decision.schema.json"
LOG_PATH = ROOT / "state" / "DECISION_LOG.jsonl"


def type_matches(value: Any, expected: str | list[str]) -> bool:
    kinds = [expected] if isinstance(expected, str) else expected
    return any(
        (kind == "null" and value is None)
        or (kind == "object" and isinstance(value, dict))
        or (kind == "array" and isinstance(value, list))
        or (kind == "string" and isinstance(value, str))
        or (kind == "integer" and isinstance(value, int) and not isinstance(value, bool))
        for kind in kinds
    )


def validate_schema(record: dict[str, Any], schema: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    for key in schema.get("required", []):
        if key not in record:
            errors.append(f"{label}: missing required field {key!r}")
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        errors.extend(f"{label}: unknown field {key!r}" for key in sorted(set(record) - set(properties)))
    for key, rule in properties.items():
        if key not in record:
            continue
        value = record[key]
        if "const" in rule and value != rule["const"]:
            errors.append(f"{label}: {key} must equal {rule['const']!r}")
        if "type" in rule and not type_matches(value, rule["type"]):
            errors.append(f"{label}: {key} has wrong type")
            continue
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"{label}: {key} must be one of {rule['enum']!r}")
        if isinstance(value, str):
            if len(value) < rule.get("minLength", 0):
                errors.append(f"{label}: {key} is too short")
            if "pattern" in rule and re.fullmatch(rule["pattern"], value) is None:
                errors.append(f"{label}: {key} does not match its required pattern")
            if rule.get("format") == "date-time":
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    errors.append(f"{label}: {key} is not an ISO-8601 date-time")
        if isinstance(value, list) and len(value) < rule.get("minItems", 0):
            errors.append(f"{label}: {key} has too few items")
        if isinstance(value, dict) and len(value) < rule.get("minProperties", 0):
            errors.append(f"{label}: {key} has too few properties")
    return errors


def validate(path: Path) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    seen: set[str] = set()
    if not path.exists():
        return [f"missing decision log: {path}"]
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        label = f"{path}:{line_number}"
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{label}: invalid JSON: {exc}")
            continue
        if not isinstance(record, dict):
            errors.append(f"{label}: decision must be an object")
            continue
        errors.extend(validate_schema(record, schema, label))
        decision_id = record.get("decision_id")
        if decision_id in seen:
            errors.append(f"{label}: duplicate decision_id {decision_id!r}")
        seen.add(decision_id)
        if decision_id != "foundation-initialization" and record.get("git_commit_sha") is None:
            errors.append(f"{label}: non-foundation decisions must record git_commit_sha")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=LOG_PATH)
    args = parser.parse_args()
    try:
        errors = validate(args.path)
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"decision validation passed: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
