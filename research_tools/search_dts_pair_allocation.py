#!/usr/bin/env python3
"""Multi-anchor difference-allocation search for a scope-111 (7,5)-DTS."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from search_dts_difference_allocation import row_mask, search_catalog
from verify_dts import verify


ROW_SIZE = 6


def make_row_with_pair(rng: random.Random, limit: int, first: int, second: int) -> tuple[int, list[int]] | None:
    if first == second or not (1 <= first <= limit and 1 <= second <= limit):
        return None
    base = {0, first, second}
    available = [value for value in range(1, limit + 1) if value not in base]
    row = [0] + sorted({first, second} | set(rng.sample(available, ROW_SIZE - 3)))
    mask = row_mask(row)
    return (mask, row) if mask is not None else None


def build_catalog(
    rng: random.Random,
    limit: int,
    rows_per_pair: int,
    deadline: float,
) -> tuple[dict[int, list[int]], int, int, int]:
    catalog: dict[int, list[int]] = {}
    attempts = 0
    valid = 0
    pairs = [(first, second) for first in range(limit, 0, -1) for second in range(first - 1, 0, -1)]
    completed_pairs = 0
    for first, second in pairs:
        if time.monotonic() >= deadline:
            break
        pair_valid = 0
        while pair_valid < rows_per_pair and time.monotonic() < deadline:
            attempts += 1
            candidate = make_row_with_pair(rng, limit, first, second)
            if candidate is None:
                continue
            valid += 1
            pair_valid += 1
            catalog.setdefault(candidate[0], candidate[1])
        if pair_valid == rows_per_pair:
            completed_pairs += 1
        else:
            break
    return catalog, attempts, valid, completed_pairs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--rows-per-pair", type=int, default=20)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--node-limit", type=int, default=2_000_000)
    parser.add_argument("--anchor-probe", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260829)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    deadline = started + args.seconds
    rng = random.Random(args.seed)
    catalog, attempts, valid, completed_pairs = build_catalog(
        rng, args.limit, args.rows_per_pair, deadline
    )
    rows, nodes, best_depth, best_gaps, catalog_size, best_trace = search_catalog(
        catalog, args.limit, deadline, args.node_limit, args.anchor_probe, rng
    )
    checked = verify(rows) if rows is not None else {"valid": False, "scope": None}
    payload = {
        "method": "targeted-pair-difference-allocation-catalog-exact-cover",
        "limit": args.limit,
        "rows_per_pair": args.rows_per_pair,
        "pair_generation": "fixed two positive marks equal to the pair anchors, then random completion and local Golomb validation",
        "completed_pairs": completed_pairs,
        "anchor_probe": args.anchor_probe,
        "seconds": args.seconds,
        "node_limit": args.node_limit,
        "seed": args.seed,
        "catalog_size": catalog_size,
        "generation_attempts": attempts,
        "valid_generated_rows": valid,
        "search_nodes": nodes,
        "best_depth": best_depth,
        "best_gaps": best_gaps,
        "best_trace": best_trace,
        "rows": rows or [],
        "verification": checked,
        "target_reached": bool(checked["valid"] and checked["scope"] <= args.limit),
        "elapsed_seconds": time.monotonic() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_reached": payload["target_reached"], "catalog_size": catalog_size, "completed_pairs": completed_pairs, "search_nodes": nodes, "best_depth": best_depth, "best_gaps": best_gaps, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
