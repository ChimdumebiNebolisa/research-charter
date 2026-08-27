#!/usr/bin/env python3
"""Run CaDiCaL on the preserved full-scope DTS CNF and verify any model."""

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


def mark_variable(row: int, position: int, value: int, limit: int) -> int:
    return (row * POSITIVE_MARKS + (position - 1)) * limit + value


def decode_model(output: str, limit: int) -> list[list[int]]:
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
                if mark_variable(row, position, value, limit) in positive
            ]
            if len(selected) != 1:
                return []
            decoded.append(selected[0])
        rows.append(decoded)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--cnf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    try:
        completed = subprocess.run(
            ["cadical", "-t", str(args.seconds), str(args.cnf)],
            capture_output=True,
            text=True,
            timeout=args.seconds + 15,
            check=False,
        )
        solver_output = completed.stdout + completed.stderr
        return_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        solver_output = stdout + stderr
        return_code = None

    status = "unknown"
    if "s SATISFIABLE" in solver_output:
        status = "sat"
    elif "s UNSATISFIABLE" in solver_output:
        status = "unsat"
    rows = decode_model(solver_output, args.limit) if status == "sat" else []
    checked = verify(rows) if rows else {"valid": False, "scope": None, "errors": ["no decoded model"]}
    payload = {
        "method": "cadical-preserved-full-one-hot-dts-scope-111",
        "limit": args.limit,
        "seconds": args.seconds,
        "solver": "CaDiCaL 2.1.3",
        "cnf_sha256": hashlib.sha256(args.cnf.read_bytes()).hexdigest(),
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
        "target_reached": payload["target_reached"],
        "elapsed_seconds": round(payload["elapsed_seconds"], 3),
        "output": str(args.output),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
