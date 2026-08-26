#!/usr/bin/env python3
"""Deterministic windowed multi-mark replacement search for DTS scope 111."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from verify_dts import verify


START_ROWS = [
    [0, 11, 58, 75, 98, 112],
    [0, 12, 32, 50, 103, 111],
    [0, 22, 41, 89, 104, 110],
    [0, 28, 52, 83, 108, 109],
    [0, 13, 62, 72, 105, 107],
    [0, 9, 16, 60, 102, 106],
    [0, 27, 30, 66, 95, 100],
]


def differences(row: list[int]) -> set[int]:
    return {row[j] - row[i] for i in range(6) for j in range(i + 1, 6)}


def enumerate_replacements(
    fixed_rows: list[list[int]],
    center: list[int],
    radius: int,
    limit: int,
    deadline: float,
) -> tuple[list[list[int]], int, int, bool]:
    used = set().union(*(differences(row) for row in fixed_rows))
    available = set(range(1, limit + 1)) - used
    candidate = [0]
    best = 0
    tested = 0
    rows_found: list[list[int]] = []

    def visit(index: int) -> bool:
        nonlocal best, tested
        if time.monotonic() >= deadline:
            return True
        if index == 6:
            tested += 1
            best = max(best, len(differences(candidate)))
            if len(differences(candidate)) == 15:
                rows_found.append(candidate[:])
            return bool(rows_found)

        low = max(index, center[index - 1] - radius)
        high = min(limit - (5 - index), center[index - 1] + radius)
        previous = candidate[-1]
        for value in range(max(previous + 1, low), high + 1):
            new_differences = {value - previous_value for previous_value in candidate}
            if not new_differences <= available:
                continue
            if len(new_differences) != len(candidate):
                continue
            candidate.append(value)
            if visit(index + 1):
                return True
            candidate.pop()
        return False

    stopped = visit(1)
    return rows_found, tested, best, stopped and not rows_found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=int, default=10)
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    fixed_rows = START_ROWS[1:]
    rows_found, tested, best, timed_out = enumerate_replacements(
        fixed_rows, START_ROWS[0][1:], args.radius, args.limit, started + args.seconds
    )
    target_reached = bool(rows_found)
    payload = {
        "method": "deterministic-windowed-multi-mark-replacement",
        "scope_limit": args.limit,
        "radius": args.radius,
        "seconds": args.seconds,
        "replaced_row": 0,
        "tested_complete_rows": tested,
        "best_partial_difference_count": best,
        "timed_out": timed_out,
        "target_reached": target_reached,
        "candidates": [],
    }
    for row in rows_found:
        rows = [row] + [other[:] for other in fixed_rows]
        payload["candidates"].append({"row": row, "verification": verify(rows)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_reached": target_reached, "tested": tested, "best_partial_difference_count": best, "timed_out": timed_out}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
