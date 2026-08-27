#!/usr/bin/env python3
"""Global random Golomb-ruler catalog with exact difference-cover branching."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from verify_dts import verify


def make_row(rng: random.Random, limit: int) -> tuple[int, list[int]] | None:
    row = [0] + sorted(rng.sample(range(1, limit + 1), 5))
    differences = [row[right] - row[left] for left in range(6) for right in range(left + 1, 6)]
    if len(set(differences)) != 15:
        return None
    return sum(1 << difference for difference in differences), row


def search_catalog(catalog: list[tuple[int, list[int]]], limit: int, deadline: float, node_limit: int) -> tuple[list[list[int]] | None, int, int, int]:
    by_difference: list[list[tuple[int, int, list[int]]]] = [[] for _ in range(limit + 1)]
    for candidate_id, (mask, row) in enumerate(catalog):
        for difference in range(1, limit + 1):
            if mask & (1 << difference):
                by_difference[difference].append((candidate_id, mask, row))

    nodes = 0
    best_depth = 0
    best_gaps = 0
    selected: list[list[int]] = []

    def dfs(used: int, gaps: int, depth: int) -> list[list[int]] | None:
        nonlocal nodes, best_depth, best_gaps
        best_depth = max(best_depth, depth)
        best_gaps = max(best_gaps, gaps)
        if time.monotonic() >= deadline or nodes >= node_limit:
            return None
        if depth == 7:
            return [row[:] for row in selected]

        uncovered = [difference for difference in range(1, limit + 1) if not (used & (1 << difference))]
        if not uncovered:
            return None
        ranked: list[tuple[int, int]] = []
        for difference in uncovered:
            compatible = sum(1 for _candidate_id, mask, _row in by_difference[difference] if not mask & used)
            ranked.append((compatible, difference))
        _count, anchor = min(ranked)

        # Covering the most constrained available difference is attempted first.
        for _candidate_id, mask, row in by_difference[anchor]:
            if time.monotonic() >= deadline or nodes >= node_limit:
                return None
            nodes += 1
            if mask & used:
                continue
            selected.append(row)
            result = dfs(used | mask, gaps, depth + 1)
            selected.pop()
            if result is not None:
                return result
        if gaps < 6:
            result = dfs(used | (1 << anchor), gaps + 1, depth)
            if result is not None:
                return result
        return None

    return dfs(0, 0, 0), nodes, best_depth, best_gaps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--catalog-size", type=int, default=250000)
    parser.add_argument("--attempt-limit", type=int, default=1500000)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--node-limit", type=int, default=2000000)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    deadline = started + args.seconds
    rng = random.Random(args.seed)
    catalog: dict[int, list[int]] = {}
    attempts = 0
    while len(catalog) < args.catalog_size and attempts < args.attempt_limit and time.monotonic() < deadline:
        attempts += 1
        candidate = make_row(rng, args.limit)
        if candidate is not None:
            catalog.setdefault(candidate[0], candidate[1])
    rows, nodes, best_depth, best_gaps = search_catalog(list(catalog.items()), args.limit, deadline, args.node_limit)
    checked = verify(rows) if rows is not None else {"valid": False, "scope": None}
    payload = {
        "method": "global-random-golomb-catalog-exact-difference-cover",
        "limit": args.limit,
        "catalog_size_target": args.catalog_size,
        "catalog_size": len(catalog),
        "attempt_limit": args.attempt_limit,
        "attempts": attempts,
        "seconds": args.seconds,
        "node_limit": args.node_limit,
        "seed": args.seed,
        "search_nodes": nodes,
        "best_depth": best_depth,
        "best_gaps": best_gaps,
        "rows": rows or [],
        "verification": checked,
        "target_reached": bool(checked["valid"] and checked["scope"] <= args.limit),
        "elapsed_seconds": time.monotonic() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_reached": payload["target_reached"], "catalog_size": payload["catalog_size"], "search_nodes": nodes, "best_depth": best_depth, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
