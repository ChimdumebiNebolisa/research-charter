#!/usr/bin/env python3
"""Z3 integer feasibility model for a scope-111 (7,5)-DTS."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from z3 import Distinct, Int, Solver, sat, unknown

from verify_dts import verify


def build_solver(limit: int, seed: int) -> tuple[Solver, list[list[object]]]:
    solver = Solver()
    solver.set(timeout=0)
    solver.set(random_seed=seed)
    marks = [[Int(f"a_{row}_{column}") for column in range(6)] for row in range(7)]
    for row in marks:
        solver.add(row[0] == 0)
        for value in row:
            solver.add(value >= 0, value <= limit)
        for left, right in zip(row, row[1:]):
            solver.add(left < right)

    differences = [
        row[right] - row[left]
        for row in marks
        for left in range(6)
        for right in range(left + 1, 6)
    ]
    solver.add(Distinct(differences))

    # Rows are interchangeable; ordering their first positive marks removes
    # the same symmetry class as the existing exact formulations.
    for previous, following in zip(marks, marks[1:]):
        solver.add(previous[1] <= following[1])
    return solver, marks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    solver, marks = build_solver(args.limit, args.seed)
    solver.set(timeout=max(1, int(args.seconds * 1000)))
    started = time.monotonic()
    status = solver.check()
    elapsed = time.monotonic() - started
    rows = []
    if status == sat:
        model = solver.model()
        rows = [[model.eval(variable).as_long() for variable in row] for row in marks]
    checked = verify(rows) if rows else {"valid": False, "scope": None}
    status_name = "sat" if status == sat else "unknown" if status == unknown else "unsat"
    payload = {
        "method": "z3-integer-distinct-differences-feasibility",
        "limit": args.limit,
        "seconds": args.seconds,
        "seed": args.seed,
        "status": status_name,
        "elapsed_seconds": elapsed,
        "rows": rows,
        "verification": checked,
        "target_reached": bool(checked["valid"] and checked["scope"] <= args.limit),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status_name, "target_reached": payload["target_reached"], "elapsed_seconds": round(elapsed, 3), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
