#!/usr/bin/env python3
"""Check experiment records for frozen-scope and repetition drift."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "problems" / "PROBLEM_REGISTRY.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def records_at(path: Path) -> list[tuple[Path, dict[str, Any]]]:
    paths = [path] if path.is_file() else sorted(path.rglob("*.json"))
    records: list[tuple[Path, dict[str, Any]]] = []
    for record_path in paths:
        record = load_json(record_path)
        if not isinstance(record, dict):
            raise ValueError(f"{record_path}: record must be an object")
        records.append((record_path, record))
    return records


def validate(path: Path) -> list[str]:
    registry = load_json(REGISTRY_PATH)
    problems = {item["problem_id"]: item for item in registry["problems"]}
    errors: list[str] = []
    records = records_at(path)
    experiment_ids = {
        record.get("experiment_id") for _, record in records if record.get("record_type") == "experiment"
    }
    fingerprints: dict[str, Path] = {}
    for record_path, record in records:
        record_type = record.get("record_type")
        if record_type not in {"experiment", "candidate"}:
            errors.append(f"{record_path}: unknown record_type {record_type!r}")
            continue
        problem_id = record.get("problem_id")
        if problem_id not in problems:
            errors.append(f"{record_path}: problem_id is not in the frozen registry")
            continue
        frozen_target = problems[problem_id]["target_id"]
        if record.get("target_id") != frozen_target:
            errors.append(f"{record_path}: target_id is not the frozen target {frozen_target!r}")
        if problems[problem_id].get("baseline_status", "").startswith("BASELINE_UNRESOLVED"):
            errors.append(f"{record_path}: research is blocked because {problem_id} has BASELINE_UNRESOLVED status")
        if record_type == "experiment":
            relation = record.get("metric_relation_to_true_objective")
            if not isinstance(relation, str) or not relation.strip():
                errors.append(f"{record_path}: metric relation to the true objective is required")
            for parent in record.get("parent_experiment_ids", []):
                if not str(parent).startswith("external:") and parent not in experiment_ids:
                    errors.append(f"{record_path}: unknown parent experiment {parent!r}")
            fingerprint_input = {
                "problem_id": problem_id,
                "target_id": record.get("target_id"),
                "hypothesis": record.get("hypothesis"),
                "method": record.get("method"),
                "metric": record.get("metric"),
                "configuration": record.get("configuration"),
            }
            fingerprint = hashlib.sha256(
                json.dumps(fingerprint_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            previous = fingerprints.get(fingerprint)
            justification = record.get("repetition_justification")
            if previous is not None and not (isinstance(justification, str) and justification.strip()):
                errors.append(f"{record_path}: duplicate experiment fingerprint without repetition_justification; first at {previous}")
            fingerprints.setdefault(fingerprint, record_path)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=ROOT / "experiments")
    args = parser.parse_args()
    try:
        errors = validate(args.path)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"drift check passed: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
