#!/usr/bin/env python3
"""Stochastic local search for a (7,5)-DTS with scope at most 111."""

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


def row_differences(row: list[int]) -> set[int] | None:
    differences = [row[j] - row[i] for i in range(6) for j in range(i + 1, 6)]
    return set(differences) if len(set(differences)) == 15 and min(row) == 0 and all(row[i] < row[i + 1] for i in range(5)) else None


def score(rows: list[list[int]], limit: int) -> tuple[int, int, int]:
    all_differences: list[int] = []
    local_failures = 0
    for row in rows:
        differences = row_differences(row)
        if differences is None:
            local_failures += 1
        else:
            all_differences.extend(differences)
    unique = len(set(all_differences))
    overflow = max(0, max((row[-1] for row in rows), default=0) - limit)
    return unique - 20 * local_failures - 3 * overflow, unique, overflow


def mutate(rows: list[list[int]], rng: random.Random, limit: int) -> list[list[int]]:
    result = [row[:] for row in rows]
    row_index = rng.randrange(7)
    mark_index = rng.randrange(1, 6)
    delta = rng.choice([-3, -2, -1, 1, 2, 3])
    row = result[row_index]
    row[mark_index] += delta
    row[mark_index] = max(1, min(limit, row[mark_index]))
    row.sort()
    row[0] = 0
    return result


def run(seed: int, seconds: float, limit: int) -> dict[str, object]:
    rng = random.Random(seed)
    deadline = time.monotonic() + seconds
    best_rows: list[list[int]] = []
    # The single mark at 112 is forced down at the beginning to make the
    # target boundary part of the initial state rather than a post-hoc filter.
    current_rows = [[min(value, limit) for value in row] for row in START_ROWS]
    current_score = score(current_rows, limit)
    best_rows = [row[:] for row in current_rows]
    best_score = current_score
    accepted = 0
    iterations = 0
    while time.monotonic() < deadline:
        iterations += 1
        temperature = max(0.05, 2.5 * (deadline - time.monotonic()) / seconds)
        candidate = mutate(current_rows, rng, limit)
        candidate_score = score(candidate, limit)
        delta = candidate_score[0] - current_score[0]
        if delta >= 0 or rng.random() < math.exp(delta / temperature):
            current_rows = candidate
            current_score = candidate_score
            accepted += 1
        if candidate_score > best_score:
            best_rows = [row[:] for row in candidate]
            best_score = candidate_score
        if best_score[1] == 105 and max(row[-1] for row in best_rows) <= limit:
            break

    result = verify(best_rows)
    return {
        "seed": seed,
        "iterations": iterations,
        "accepted": accepted,
        "best_score": best_score,
        "best_rows": best_rows,
        "verification": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--seconds-per-seed", type=float, default=30.0)
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runs = [run(seed, args.seconds_per_seed, args.limit) for seed in args.seed]
    best = max(runs, key=lambda item: tuple(item["best_score"]))
    payload = {
        "method": "scope-111-clamped-simulated-annealing-local-perturbation",
        "limit": args.limit,
        "seconds_per_seed": args.seconds_per_seed,
        "runs": runs,
        "best_run": best,
        "target_reached": bool(best["verification"]["valid"] and best["verification"]["scope"] <= args.limit),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_reached": payload["target_reached"], "best_score": best["best_score"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
