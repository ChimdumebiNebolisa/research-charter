#!/usr/bin/env python3
"""Conflict-directed multi-mark/multi-row annealing for DTS scope 111."""

from __future__ import annotations

import argparse
import json
import math
import random
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


def score(rows: list[list[int]], limit: int) -> tuple[int, int, int, int]:
    all_differences = [row[j] - row[i] for row in rows for i in range(6) for j in range(i + 1, 6)]
    local_failures = sum(
        len({row[j] - row[i] for i in range(6) for j in range(i + 1, 6)}) != 15
        or any(row[i] >= row[i + 1] for i in range(5))
        for row in rows
    )
    unique = len(set(all_differences))
    overflow = sum(max(0, value - limit) for row in rows for value in row)
    objective = unique - 20 * local_failures - 3 * overflow
    return objective, unique, local_failures, overflow


def mutate(rows: list[list[int]], rng: random.Random, limit: int) -> list[list[int]]:
    result = [row[:] for row in rows]
    row_index = rng.randrange(7)
    if rng.random() < 0.2:
        result[row_index] = [0] + sorted(rng.sample(range(1, limit + 1), 5))
        return result
    marks = rng.sample(range(1, 6), 2)
    for mark_index in marks:
        result[row_index][mark_index] += rng.randint(-15, 15)
        result[row_index][mark_index] = max(1, min(limit + 5, result[row_index][mark_index]))
    result[row_index][1:] = sorted(result[row_index][1:])
    result[row_index][0] = 0
    return result


def run(seed: int, seconds: float, limit: int) -> dict[str, object]:
    rng = random.Random(seed)
    deadline = time.monotonic() + seconds
    current = [[min(value, limit) for value in row] for row in START_ROWS]
    current_score = score(current, limit)
    best = [row[:] for row in current]
    best_score = current_score
    accepted = 0
    iterations = 0
    while time.monotonic() < deadline:
        iterations += 1
        candidate = mutate(current, rng, limit)
        candidate_score = score(candidate, limit)
        remaining_ratio = max(0.01, (deadline - time.monotonic()) / seconds)
        temperature = max(0.1, 5.0 * remaining_ratio)
        delta = candidate_score[0] - current_score[0]
        if delta >= 0 or rng.random() < math.exp(delta / temperature):
            current, current_score = candidate, candidate_score
            accepted += 1
        if candidate_score > best_score:
            best, best_score = [row[:] for row in candidate], candidate_score
        checked = verify(best)
        if checked["valid"] and checked["scope"] <= limit:
            return {"seed": seed, "iterations": iterations, "accepted": accepted, "best_score": best_score, "best_rows": best, "verification": checked, "target_reached": True}
    return {"seed": seed, "iterations": iterations, "accepted": accepted, "best_score": best_score, "best_rows": best, "verification": verify(best), "target_reached": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--seconds-per-seed", type=float, default=30.0)
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runs = [run(seed, args.seconds_per_seed, args.limit) for seed in args.seed]
    best = max(runs, key=lambda item: tuple(item["best_score"]))
    payload = {"method": "conflict-directed-two-mark-and-row-replacement-annealing", "limit": args.limit, "seconds_per_seed": args.seconds_per_seed, "runs": runs, "best_run": best, "target_reached": bool(best["target_reached"])}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_reached": payload["target_reached"], "best_score": best["best_score"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
