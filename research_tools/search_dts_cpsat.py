#!/usr/bin/env python3
"""CP-SAT feasibility model for a scope-111 (7,5)-DTS."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ortools.sat.python import cp_model

from verify_dts import verify


def build_model(limit: int) -> tuple[cp_model.CpModel, list[list[cp_model.IntVar]], list[cp_model.IntVar]]:
    model = cp_model.CpModel()
    marks = [[model.new_int_var(0, limit, f"a_{row}_{col}") for col in range(6)] for row in range(7)]
    for row in marks:
        model.add(row[0] == 0)
        for left, right in zip(row, row[1:]):
            model.add(left + 1 <= right)

    differences: list[cp_model.IntVar] = []
    for row in marks:
        for left in range(6):
            for right in range(left + 1, 6):
                difference = model.new_int_var(1, limit, f"d_{len(differences)}")
                model.add(difference == row[right] - row[left])
                differences.append(difference)
    model.add_all_different(differences)

    # A safe partial symmetry break: rows are interchangeable, so their first
    # positive marks may be ordered without excluding any equivalence class.
    for previous, following in zip(marks, marks[1:]):
        model.add(previous[1] <= following[1])
    return model, marks, differences


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    model, marks, _differences = build_model(args.limit)
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
        "method": "cp-sat-all-differences-distinct-feasibility",
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
