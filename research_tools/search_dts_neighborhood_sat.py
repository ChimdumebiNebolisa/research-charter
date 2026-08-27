#!/usr/bin/env python3
"""Clause-learning SAT exact-cover search over a DTS baseline neighborhood."""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path

from pysat.card import CardEnc, EncType
from pysat.formula import CNF
from pysat.solvers import Glucose4

from search_dts_neighborhood_exact import START_ROWS, build_pool
from verify_dts import verify


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=int, default=3)
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pools = []
    attempts = []
    for center in START_ROWS:
        pool, tried = build_pool(center, args.radius, args.limit)
        pools.append(pool)
        attempts.append(tried)

    candidate_count = sum(len(pool) for pool in pools)
    row_variables: list[list[int]] = []
    next_variable = 0
    for pool in pools:
        literals = list(range(next_variable + 1, next_variable + len(pool) + 1))
        row_variables.append(literals)
        next_variable += len(pool)

    formula = CNF()
    for literals in row_variables:
        encoded = CardEnc.equals(literals, bound=1, top_id=next_variable, encoding=EncType.seqcounter)
        formula.extend(encoded.clauses)
        next_variable = encoded.nv

    for difference in range(1, args.limit + 1):
        literals = [
            variable
            for variables, pool in zip(row_variables, pools)
            for variable, (mask, _row) in zip(variables, pool)
            if mask & (1 << difference)
        ]
        if literals:
            encoded = CardEnc.atmost(literals, bound=1, top_id=next_variable, encoding=EncType.seqcounter)
            formula.extend(encoded.clauses)
            next_variable = encoded.nv

    solver = Glucose4(bootstrap_with=formula.clauses)
    timer = threading.Timer(args.seconds, solver.interrupt)
    started = time.monotonic()
    timer.start()
    try:
        solved = solver.solve_limited(expect_interrupt=True)
    finally:
        timer.cancel()
    elapsed = time.monotonic() - started

    status = "sat" if solved is True else "unsat" if solved is False else "unknown"
    rows = []
    if solved is True:
        positive = set(value for value in solver.get_model() if value > 0)
        for variables, pool in zip(row_variables, pools):
            chosen = next(index for index, variable in enumerate(variables) if variable in positive)
            rows.append(pool[chosen][1])
    checked = verify(rows) if rows else {"valid": False, "scope": None}
    payload = {
        "method": "glucose4-cardinality-sat-exact-cover-over-baseline-neighborhood",
        "radius": args.radius,
        "limit": args.limit,
        "seconds": args.seconds,
        "seed": args.seed,
        "pool_attempts": attempts,
        "pool_sizes": [len(pool) for pool in pools],
        "candidate_count": candidate_count,
        "boolean_variables": next_variable,
        "clause_count": len(formula.clauses),
        "status": status,
        "elapsed_seconds": elapsed,
        "rows": rows,
        "verification": checked,
        "target_reached": bool(checked["valid"] and checked["scope"] <= args.limit),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "target_reached": payload["target_reached"], "elapsed_seconds": round(elapsed, 3), "candidate_count": candidate_count, "clauses": len(formula.clauses), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
