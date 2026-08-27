#!/usr/bin/env python3
"""Encode the full scope-111 DTS decision problem for Kissat.

The encoding uses one-hot variables for the 35 positive marks.  For every
within-row difference and every possible value, an auxiliary literal records
that the difference is present; pairwise at-most-one clauses then enforce
global difference uniqueness.  The search solver is not the DTS verifier:
any decoded model is checked independently with ``verify_dts``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from verify_dts import verify


ROWS = 7
POSITIVE_MARKS = 5


class CnfBuilder:
    def __init__(self) -> None:
        self.next_variable = 0
        self.clauses: list[list[int]] = []

    def new_variable(self) -> int:
        self.next_variable += 1
        return self.next_variable

    def add(self, *literals: int) -> None:
        self.clauses.append(list(literals))


def add_at_most_one(builder: CnfBuilder, variables: list[int]) -> None:
    for left in range(len(variables)):
        for right in range(left + 1, len(variables)):
            builder.add(-variables[left], -variables[right])


def build_formula(limit: int) -> tuple[CnfBuilder, dict[tuple[int, int, int], int], dict[int, list[int]]]:
    builder = CnfBuilder()
    marks: dict[tuple[int, int, int], int] = {}
    for row in range(ROWS):
        for position in range(1, POSITIVE_MARKS + 1):
            variables = [builder.new_variable() for _value in range(1, limit + 1)]
            for value, variable in enumerate(variables, start=1):
                marks[row, position, value] = variable
            builder.add(*variables)
            add_at_most_one(builder, variables)

        # Strictly increasing marks.
        for position in range(1, POSITIVE_MARKS):
            for left_value in range(1, limit + 1):
                for right_value in range(1, left_value + 1):
                    builder.add(
                        -marks[row, position, left_value],
                        -marks[row, position + 1, right_value],
                    )

    # Row interchangeability: first positive marks are nondecreasing.
    for row in range(ROWS - 1):
        for left_value in range(1, limit + 1):
            for right_value in range(1, left_value):
                builder.add(
                    -marks[row, 1, left_value],
                    -marks[row + 1, 1, right_value],
                )

    difference_variables: dict[int, list[int]] = {difference: [] for difference in range(1, limit + 1)}
    for row in range(ROWS):
        for left_position in range(POSITIVE_MARKS + 1):
            for right_position in range(left_position + 1, POSITIVE_MARKS + 1):
                for difference in range(1, limit + 1):
                    occurrence = builder.new_variable()
                    difference_variables[difference].append(occurrence)
                    if left_position == 0:
                        if difference <= limit:
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
        add_at_most_one(builder, variables)
    return builder, marks, difference_variables


def write_dimacs(path: Path, builder: CnfBuilder) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {builder.next_variable} {len(builder.clauses)}\n")
        for clause in builder.clauses:
            output.write(" ".join(str(literal) for literal in clause) + " 0\n")


def decode_model(output: str, marks: dict[tuple[int, int, int], int], limit: int) -> list[list[int]]:
    positive: set[int] = set()
    for line in output.splitlines():
        if not line.startswith("v"):
            continue
        for token in line.split()[1:]:
            value = int(token)
            if value > 0:
                positive.add(value)
    rows: list[list[int]] = []
    for row in range(ROWS):
        decoded = [0]
        for position in range(1, POSITIVE_MARKS + 1):
            selected = [
                value
                for value in range(1, limit + 1)
                if marks[row, position, value] in positive
            ]
            if len(selected) != 1:
                return []
            decoded.append(selected[0])
        rows.append(decoded)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--cnf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    builder, marks, difference_variables = build_formula(args.limit)
    write_dimacs(args.cnf, builder)
    cnf_sha256 = hashlib.sha256(args.cnf.read_bytes()).hexdigest()
    try:
        completed = subprocess.run(
            ["kissat", f"--time={args.seconds}", str(args.cnf)],
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
        "method": "kissat-full-one-hot-dts-scope-111",
        "limit": args.limit,
        "seconds": args.seconds,
        "solver": "Kissat 4.0.3",
        "variables": builder.next_variable,
        "clauses": len(builder.clauses),
        "difference_auxiliary_variables": sum(len(values) for values in difference_variables.values()),
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
        "target_reached": payload["target_reached"],
        "elapsed_seconds": round(payload["elapsed_seconds"], 3),
        "output": str(args.output),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
