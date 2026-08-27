#!/usr/bin/env python3
"""Encode the full scope-111 DTS problem with sequential-counter AMO clauses.

This keeps the one-hot mark and exact difference-occurrence formulation from
the symmetry experiment, but replaces every pairwise at-most-one family with
the linear-size sequential counter encoding of Sinz.  The stronger exact row
and reflection symmetry breaks are retained.  Any decoded model is checked
independently with ``verify_dts``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from search_dts_kissat_symmetry import (
    POSITIVE_MARKS,
    ROWS,
    CnfBuilder,
    add_lexicographic_row_symmetry,
    add_reflection_symmetry,
    decode_model,
    write_dimacs,
)
from verify_dts import verify


def add_sequential_at_most_one(builder: CnfBuilder, variables: list[int]) -> int:
    """Add Sinz's sequential at-most-one encoding and return auxiliaries used."""
    if len(variables) < 2:
        return 0
    prefix = [builder.new_variable() for _ in range(len(variables) - 1)]
    builder.add(-variables[0], prefix[0])
    for index in range(1, len(variables) - 1):
        builder.add(-variables[index], prefix[index])
        builder.add(-prefix[index - 1], prefix[index])
        builder.add(-variables[index], -prefix[index - 1])
    builder.add(-variables[-1], -prefix[-1])
    return len(prefix)


def build_formula(
    limit: int,
) -> tuple[CnfBuilder, dict[tuple[int, int, int], int], dict[int, list[int]], int]:
    builder = CnfBuilder()
    marks: dict[tuple[int, int, int], int] = {}
    sequential_variables = 0
    for row in range(ROWS):
        for position in range(1, POSITIVE_MARKS + 1):
            variables = [builder.new_variable() for _value in range(1, limit + 1)]
            for value, variable in enumerate(variables, start=1):
                marks[row, position, value] = variable
            builder.add(*variables)
            sequential_variables += add_sequential_at_most_one(builder, variables)

        # Strictly increasing marks.
        for position in range(1, POSITIVE_MARKS):
            for left_value in range(1, limit + 1):
                for right_value in range(1, left_value + 1):
                    builder.add(
                        -marks[row, position, left_value],
                        -marks[row, position + 1, right_value],
                    )

    add_lexicographic_row_symmetry(builder, marks, limit)
    add_reflection_symmetry(builder, marks, limit)

    difference_variables: dict[int, list[int]] = {difference: [] for difference in range(1, limit + 1)}
    for row in range(ROWS):
        for left_position in range(POSITIVE_MARKS + 1):
            for right_position in range(left_position + 1, POSITIVE_MARKS + 1):
                for difference in range(1, limit + 1):
                    occurrence = builder.new_variable()
                    difference_variables[difference].append(occurrence)
                    if left_position == 0:
                        builder.add(-marks[row, right_position, difference], occurrence)
                        continue
                    for left_value in range(1, limit - difference + 1):
                        right_value = left_value + difference
                        builder.add(
                            -marks[row, left_position, left_value],
                            -marks[row, right_position, right_value],
                            occurrence,
                        )

    for variables in difference_variables.values():
        sequential_variables += add_sequential_at_most_one(builder, variables)
    return builder, marks, difference_variables, sequential_variables


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--cnf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    builder, marks, difference_variables, sequential_variables = build_formula(args.limit)
    write_dimacs(args.cnf, builder)
    cnf_sha256 = hashlib.sha256(args.cnf.read_bytes()).hexdigest()
    try:
        seconds_argument = str(int(args.seconds)) if args.seconds.is_integer() else str(args.seconds)
        completed = subprocess.run(
            ["kissat", f"--time={seconds_argument}", str(args.cnf)],
            capture_output=True,
            text=True,
            timeout=args.seconds + 15.0,
            check=False,
        )
        solver_output = completed.stdout + completed.stderr
        return_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        solver_output = (error.stdout or "") + (error.stderr or "")
        return_code = None

    status = "unknown"
    if "s SATISFIABLE" in solver_output:
        status = "sat"
    elif "s UNSATISFIABLE" in solver_output:
        status = "unsat"
    rows = decode_model(solver_output, marks, args.limit) if status == "sat" else []
    checked = verify(rows) if rows else {"valid": False, "scope": None}
    payload = {
        "method": "kissat-full-one-hot-dts-scope-111-with-sequential-amo-and-symmetry",
        "limit": args.limit,
        "seconds": args.seconds,
        "solver": "Kissat 4.0.3",
        "variables": builder.next_variable,
        "clauses": len(builder.clauses),
        "difference_auxiliary_variables": sum(len(values) for values in difference_variables.values()),
        "sequential_counter_variables": sequential_variables,
        "symmetry_break": {
            "row_order": "complete lexicographic ordering on all five positive marks",
            "row_reflection": "a1+a4<=a5 for every normalized row",
        },
        "cnf_sha256": cnf_sha256,
        "status": status,
        "solver_return_code": return_code,
        "solver_output": solver_output,
        "elapsed_seconds": time.monotonic() - started,
        "rows": rows,
        "verification": checked,
        "target_reached": bool(checked["valid"] and checked["scope"] <= args.limit),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.raw.parent.mkdir(parents=True, exist_ok=True)
    args.raw.write_text(solver_output, encoding="utf-8")
    print(json.dumps({
        "status": status,
        "variables": builder.next_variable,
        "clauses": len(builder.clauses),
        "sequential_counter_variables": sequential_variables,
        "target_reached": payload["target_reached"],
        "elapsed_seconds": round(payload["elapsed_seconds"], 3),
        "output": str(args.output),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
