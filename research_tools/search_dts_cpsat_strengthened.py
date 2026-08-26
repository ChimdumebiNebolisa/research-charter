#!/usr/bin/env python3
"""Strengthened CP-SAT model for a scope-111 (7,5)-DTS."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ortools.sat.python import cp_model

from search_dts_cpsat import build_model
from verify_dts import verify


def add_lexicographic_leq(model: cp_model.CpModel, left: list[cp_model.IntVar], right: list[cp_model.IntVar], label: str) -> None:
    """Enforce left <= right lexicographically with reified Boolean chains."""
    prefixes = [model.new_bool_var(f"{label}_prefix_{index}") for index in range(len(left) + 1)]
    model.add(prefixes[0] == 1)
    terms: list[cp_model.BoolVarT] = []
    for index, (left_value, right_value) in enumerate(zip(left, right)):
        equal = model.new_bool_var(f"{label}_equal_{index}")
        model.add(left_value == right_value).only_enforce_if(equal)
        model.add(left_value != right_value).only_enforce_if(equal.Not())
        model.add_bool_and([prefixes[index], equal]).only_enforce_if(prefixes[index + 1])
        model.add_bool_or([prefixes[index].Not(), equal.Not()]).only_enforce_if(prefixes[index + 1].Not())

        less = model.new_bool_var(f"{label}_less_{index}")
        model.add(left_value < right_value).only_enforce_if(less)
        model.add(left_value >= right_value).only_enforce_if(less.Not())
        term = model.new_bool_var(f"{label}_term_{index}")
        model.add_bool_and([prefixes[index], less]).only_enforce_if(term)
        model.add_bool_or([prefixes[index].Not(), less.Not()]).only_enforce_if(term.Not())
        terms.append(term)
    model.add_bool_or(terms + [prefixes[-1]])


def build_strengthened_model(limit: int) -> tuple[cp_model.CpModel, list[list[cp_model.IntVar]]]:
    model, marks, _differences = build_model(limit)
    positive_marks = [marks[row][column] for row in range(7) for column in range(1, 6)]
    model.add_all_different(positive_marks)
    for index in range(6):
        add_lexicographic_leq(model, marks[index], marks[index + 1], f"row_{index}")
    return model, marks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    model, marks = build_strengthened_model(args.limit)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.seconds
    solver.parameters.num_search_workers = args.workers
    solver.parameters.random_seed = args.seed
    solver.parameters.log_search_progress = False
    started = time.monotonic()
    status = solver.solve(model)
    elapsed = time.monotonic() - started
    rows = [[solver.value(variable) for variable in row] for row in marks] if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else []
    checked = verify(rows) if rows else {"valid": False, "scope": None}
    payload = {
        "method": "cp-sat-strengthened-mark-alldifferent-and-lex-row-symmetry",
        "limit": args.limit,
        "seconds": args.seconds,
        "workers": args.workers,
        "seed": args.seed,
        "status": solver.status_name(status),
        "status_code": int(status),
        "elapsed_seconds": elapsed,
        "objective_bound": None,
        "rows": rows,
        "verification": checked,
        "target_reached": bool(checked["valid"] and checked["scope"] <= args.limit),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "target_reached": payload["target_reached"], "elapsed_seconds": round(elapsed, 3), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
