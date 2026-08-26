#!/usr/bin/env python3
"""Compatibility-indexed candidate-pool backtracking for DTS scope 111."""

from __future__ import annotations

import argparse
import json
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
VARIABLE_ROWS = (0, 1, 4, 6)
FIXED_ROWS = (2, 3, 5)


def mask_for(row: list[int], limit: int) -> int | None:
    if len(row) != 6 or row[0] != 0 or row[-1] > limit or any(row[i] >= row[i + 1] for i in range(5)):
        return None
    differences = [row[j] - row[i] for i in range(6) for j in range(i + 1, 6)]
    if len(set(differences)) != 15:
        return None
    return sum(1 << difference for difference in differences)


def make_row(rng: random.Random, center: list[int], limit: int, radius: int) -> list[int]:
    if rng.random() < 0.75:
        values = [max(1, min(limit, center[index] + rng.randint(-radius, radius))) for index in range(1, 6)]
    else:
        values = rng.sample(range(1, limit + 1), 5)
    return [0] + sorted(values)


def build_pool(
    rng: random.Random,
    center: list[int],
    fixed_mask: int,
    limit: int,
    radius: int,
    pool_size: int,
    attempt_limit: int,
    deadline: float,
) -> tuple[list[tuple[int, list[int]]], int, int]:
    pool: dict[int, list[int]] = {}
    attempts = 0
    while len(pool) < pool_size and attempts < attempt_limit and time.monotonic() < deadline:
        attempts += 1
        row = make_row(rng, center, limit, radius)
        mask = mask_for(row, limit)
        if mask is not None and not mask & fixed_mask:
            pool.setdefault(mask, row)
    return list(pool.items()), attempts, len(pool)


def run(seed: int, seconds: float, limit: int, radius: int, pool_size: int, node_limit: int, pool_seconds: float, pool_attempt_limit: int) -> dict[str, object]:
    rng = random.Random(seed)
    deadline = time.monotonic() + seconds
    fixed_mask = 0
    for index in FIXED_ROWS:
        mask = mask_for(START_ROWS[index], limit)
        if mask is None:
            raise ValueError("fixed row is not valid under the requested scope")
        fixed_mask |= mask

    pools: dict[int, list[tuple[int, list[int]]]] = {}
    pool_attempts: dict[int, int] = {}
    for index in VARIABLE_ROWS:
        pool_deadline = min(deadline, time.monotonic() + pool_seconds)
        pool, attempts, _unique = build_pool(rng, START_ROWS[index], fixed_mask, limit, radius, pool_size, pool_attempt_limit, pool_deadline)
        rng.shuffle(pool)
        pools[index] = pool
        pool_attempts[index] = attempts

    order = sorted((index for index in VARIABLE_ROWS if index in pools), key=lambda index: len(pools[index]))
    nodes = 0
    solution: list[list[int]] | None = None
    best_depth = 0

    def dfs(depth: int, used: int, selected: dict[int, list[int]]) -> bool:
        nonlocal nodes, solution, best_depth
        if time.monotonic() >= deadline or nodes >= node_limit:
            return False
        best_depth = max(best_depth, depth)
        if depth == len(order):
            solution = [START_ROWS[index][:] for index in range(7)]
            for index, row in selected.items():
                solution[index] = row[:]
            return True
        index = order[depth]
        for mask, row in pools[index]:
            nodes += 1
            if not mask & used:
                selected[index] = row
                if dfs(depth + 1, used | mask, selected):
                    return True
                selected.pop(index)
        return False

    found = len(order) == len(VARIABLE_ROWS) and dfs(0, fixed_mask, {})
    if found and solution is not None:
        checked = verify(solution)
        target_reached = bool(checked["valid"] and checked["scope"] <= limit)
    else:
        checked = {"valid": False, "scope": limit}
        target_reached = False
    return {"seed": seed, "pool_sizes": {str(index): len(pools.get(index, [])) for index in VARIABLE_ROWS}, "pool_attempts": {str(index): pool_attempts.get(index, 0) for index in VARIABLE_ROWS}, "backtracking_order": order, "nodes": nodes, "best_depth": best_depth, "target_reached": target_reached, "best_rows": solution if solution is not None else [], "verification": checked}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--seconds-per-seed", type=float, default=30.0)
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--radius", type=int, default=25)
    parser.add_argument("--pool-size", type=int, default=5000)
    parser.add_argument("--pool-seconds", type=float, default=5.0)
    parser.add_argument("--pool-attempt-limit", type=int, default=200000)
    parser.add_argument("--node-limit", type=int, default=500000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runs = [run(seed, args.seconds_per_seed, args.limit, args.radius, args.pool_size, args.node_limit, args.pool_seconds, args.pool_attempt_limit) for seed in args.seed]
    best = max(runs, key=lambda item: (item["target_reached"], item["best_depth"], -item["nodes"]))
    payload = {"method": "compatibility-indexed-candidate-pool-backtracking", "limit": args.limit, "radius": args.radius, "pool_size": args.pool_size, "pool_seconds": args.pool_seconds, "pool_attempt_limit": args.pool_attempt_limit, "node_limit": args.node_limit, "seconds_per_seed": args.seconds_per_seed, "runs": runs, "best_run": best, "target_reached": bool(best["target_reached"])}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_reached": payload["target_reached"], "best_depth": best["best_depth"], "pool_sizes": best["pool_sizes"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
