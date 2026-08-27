#!/usr/bin/env python3
"""Candidate-level CP-SAT exact-cover search over a DTS baseline neighborhood."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ortools.sat.python import cp_model

from search_dts_neighborhood_exact import START_ROWS, build_pool
from verify_dts import verify


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=int, default=3)
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pools = []
    attempts = []
    for center in START_ROWS:
        pool, tried = build_pool(center, args.radius, args.limit)
        pools.append(pool)
        attempts.append(tried)

    model = cp_model.CpModel()
    selected = []
    for row_index, pool in enumerate(pools):
        variables = [model.new_bool_var(f"row_{row_index}_candidate_{candidate_index}") for candidate_index in range(len(pool))]
        model.add_exactly_one(variables)
        selected.append(variables)

    for difference in range(1, args.limit + 1):
        incidence = [
            variable
            for variables, pool in zip(selected, pools)
            for variable, (mask, _row) in zip(variables, pool)
            if mask & (1 << difference)
        ]
        if incidence:
            model.add(sum(incidence) <= 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.seconds
    solver.parameters.num_search_workers = args.workers
    solver.parameters.random_seed = args.seed
    solver.parameters.log_search_progress = False
    started = time.monotonic()
    status = solver.solve(model)
    elapsed = time.monotonic() - started
    rows = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for variables, pool in zip(selected, pools):
            chosen = next(index for index, variable in enumerate(variables) if solver.value(variable))
            rows.append(pool[chosen][1])
    checked = verify(rows) if rows else {"valid": False, "scope": None}
    status_name = solver.status_name(status)
    payload = {
        "method": "candidate-level-cpsat-exact-cover-over-baseline-neighborhood",
        "radius": args.radius,
        "limit": args.limit,
        "seconds": args.seconds,
        "workers": args.workers,
        "seed": args.seed,
        "pool_attempts": attempts,
        "pool_sizes": [len(pool) for pool in pools],
        "candidate_count": sum(len(pool) for pool in pools),
        "status": status_name,
        "status_code": int(status),
        "elapsed_seconds": elapsed,
        "objective_bound": None,
        "rows": rows,
        "verification": checked,
        "target_reached": bool(checked["valid"] and checked["scope"] <= args.limit),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status_name, "target_reached": payload["target_reached"], "elapsed_seconds": round(elapsed, 3), "candidate_count": payload["candidate_count"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
