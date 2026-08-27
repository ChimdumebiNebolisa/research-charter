#!/usr/bin/env python3
"""Exact-cover search over a bounded all-row neighborhood of the DTS baseline."""

from __future__ import annotations

import argparse
import itertools
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


def row_mask(row: list[int], limit: int) -> int | None:
    if row[0] != 0 or row[-1] > limit or any(left >= right for left, right in zip(row, row[1:])):
        return None
    differences = [row[right] - row[left] for left in range(6) for right in range(left + 1, 6)]
    if len(set(differences)) != 15:
        return None
    return sum(1 << difference for difference in differences)


def build_pool(center: list[int], radius: int, limit: int) -> tuple[list[tuple[int, list[int]]], int]:
    pool: dict[int, list[int]] = {}
    attempted = 0
    for deltas in itertools.product(range(-radius, radius + 1), repeat=5):
        attempted += 1
        row = [0] + [center[index] + deltas[index - 1] for index in range(1, 6)]
        mask = row_mask(row, limit)
        if mask is not None:
            pool.setdefault(mask, row)
    return list(pool.items()), attempted


def run(radius: int, limit: int, seconds: float, node_limit: int) -> dict[str, object]:
    deadline = time.monotonic() + seconds
    pools: list[list[tuple[int, list[int]]]] = []
    attempts: list[int] = []
    for center in START_ROWS:
        pool, tried = build_pool(center, radius, limit)
        pools.append(pool)
        attempts.append(tried)
    order = sorted(range(7), key=lambda index: len(pools[index]))
    nodes = 0
    best_depth = 0
    selected: dict[int, list[int]] = {}
    solution: list[list[int]] | None = None

    def dfs(depth: int, used: int) -> bool:
        nonlocal nodes, best_depth, solution
        if time.monotonic() >= deadline or nodes >= node_limit:
            return False
        best_depth = max(best_depth, depth)
        if depth == len(order):
            solution = [selected[index][:] for index in range(7)]
            return True
        index = order[depth]
        for mask, row in pools[index]:
            if time.monotonic() >= deadline or nodes >= node_limit:
                return False
            nodes += 1
            if mask & used:
                continue
            selected[index] = row
            if dfs(depth + 1, used | mask):
                return True
            selected.pop(index)
        return False

    found = dfs(0, 0)
    checked = verify(solution) if found and solution is not None else {"valid": False, "scope": None}
    return {
        "radius": radius,
        "limit": limit,
        "pool_sizes": [len(pool) for pool in pools],
        "pool_attempts": attempts,
        "row_order": order,
        "nodes": nodes,
        "best_depth": best_depth,
        "search_complete": time.monotonic() < deadline and nodes < node_limit and (found or best_depth < 7),
        "rows": solution or [],
        "verification": checked,
        "target_reached": bool(checked["valid"] and checked["scope"] <= limit),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=int, default=3)
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--node-limit", type=int, default=5_000_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = run(args.radius, args.limit, args.seconds, args.node_limit)
    result["elapsed_seconds"] = time.monotonic() - started
    result["method"] = "exact-all-row-baseline-neighborhood-compatible-cover"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_reached": result["target_reached"], "best_depth": result["best_depth"], "pool_sizes": result["pool_sizes"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
