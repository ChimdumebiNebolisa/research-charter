#!/usr/bin/env python3
"""Targeted difference-allocation search for a scope-111 (7,5)-DTS.

Unlike the uniform catalog search, rows are generated conditional on an
uncovered difference.  Exact-cover recursion then branches on a scarce
currently compatible difference, allowing at most six omitted differences.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from pathlib import Path

from verify_dts import verify


ROW_SIZE = 6
ROW_DIFFERENCES = 15


def row_mask(row: list[int]) -> int | None:
    differences = [row[right] - row[left] for left in range(ROW_SIZE) for right in range(left + 1, ROW_SIZE)]
    if len(set(differences)) != ROW_DIFFERENCES:
        return None
    return sum(1 << difference for difference in differences)


def make_row_with_anchor(rng: random.Random, limit: int, anchor: int) -> tuple[int, list[int]] | None:
    """Generate a valid Golomb ruler containing ``anchor`` as a difference."""
    offset = rng.randrange(limit - anchor + 1)
    base = {0, offset, offset + anchor}
    base.discard(0)
    available = [value for value in range(1, limit + 1) if value not in base]
    needed = ROW_SIZE - 1 - len(base)
    if needed < 0 or needed > len(available):
        return None
    row = [0] + sorted(base | set(rng.sample(available, needed)))
    mask = row_mask(row)
    return (mask, row) if mask is not None else None


def build_catalog(
    rng: random.Random,
    limit: int,
    rows_per_anchor: int,
    deadline: float,
) -> tuple[dict[int, list[int]], int, int, dict[int, int]]:
    catalog: dict[int, list[int]] = {}
    attempts = 0
    valid = 0
    generated_by_anchor: Counter[int] = Counter()
    anchors = list(range(limit, 0, -1))
    while time.monotonic() < deadline and any(generated_by_anchor[anchor] < rows_per_anchor for anchor in anchors):
        for anchor in anchors:
            if time.monotonic() >= deadline:
                break
            if generated_by_anchor[anchor] >= rows_per_anchor:
                continue
            attempts += 1
            candidate = make_row_with_anchor(rng, limit, anchor)
            if candidate is None:
                continue
            valid += 1
            generated_by_anchor[anchor] += 1
            catalog.setdefault(candidate[0], candidate[1])
    return catalog, attempts, valid, dict(generated_by_anchor)


def search_catalog(
    catalog: dict[int, list[int]],
    limit: int,
    deadline: float,
    node_limit: int,
    anchor_probe: int,
    rng: random.Random,
) -> tuple[list[list[int]] | None, int, int, int, int, list[int]]:
    entries = [(mask, row) for mask, row in catalog.items()]
    by_difference: list[list[tuple[int, list[int]]]] = [[] for _ in range(limit + 1)]
    for mask, row in entries:
        for difference in range(1, limit + 1):
            if mask & (1 << difference):
                by_difference[difference].append((mask, row))

    static_order = sorted(
        range(1, limit + 1),
        key=lambda difference: (len(by_difference[difference]), -difference),
    )
    selected: list[list[int]] = []
    nodes = 0
    best_depth = 0
    best_gaps = 0
    best_rows: list[list[int]] = []
    best_trace: list[int] = []

    def compatible(anchor: int, used: int) -> list[tuple[int, list[int]]]:
        return [(mask, row) for mask, row in by_difference[anchor] if not (mask & used)]

    def dfs(used: int, gaps: int, depth: int, trace: list[int]) -> list[list[int]] | None:
        nonlocal nodes, best_depth, best_gaps, best_rows, best_trace
        if time.monotonic() >= deadline or nodes >= node_limit:
            return None
        if depth > best_depth or (depth == best_depth and gaps > best_gaps):
            best_depth = depth
            best_gaps = gaps
            best_rows = [row[:] for row in selected]
            best_trace = trace[:]
        if depth == 7:
            return [row[:] for row in selected]

        ranked: list[tuple[int, int, list[tuple[int, list[int]]]]] = []
        for difference in static_order[:anchor_probe]:
            if used & (1 << difference):
                continue
            candidates = compatible(difference, used)
            ranked.append((len(candidates), difference, candidates))
        if not ranked:
            return None
        count, anchor, candidates = min(ranked, key=lambda item: (item[0], -item[1]))
        if count == 0:
            if gaps >= 6:
                return None
            nodes += 1
            return dfs(used | (1 << anchor), gaps + 1, depth, trace + [anchor])

        uncovered = [difference for difference in range(1, limit + 1) if not (used & (1 << difference))]
        static_rank = {difference: index for index, difference in enumerate(static_order)}
        rng.shuffle(candidates)
        candidates.sort(
            key=lambda item: (
                -sum(1.0 / (1.0 + static_rank[difference]) for difference in uncovered if item[0] & (1 << difference)),
                item[1][-1],
            )
        )
        for mask, row in candidates:
            if time.monotonic() >= deadline or nodes >= node_limit:
                return None
            nodes += 1
            selected.append(row)
            result = dfs(used | mask, gaps, depth + 1, trace + [anchor])
            selected.pop()
            if result is not None:
                return result
        if gaps < 6:
            nodes += 1
            result = dfs(used | (1 << anchor), gaps + 1, depth, trace + [anchor])
            if result is not None:
                return result
        return None

    result = dfs(0, 0, 0, [])
    return result, nodes, best_depth, best_gaps, len(entries), best_trace


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--rows-per-anchor", type=int, default=400)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--node-limit", type=int, default=2_000_000)
    parser.add_argument("--anchor-probe", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    deadline = started + args.seconds
    rng = random.Random(args.seed)
    catalog, attempts, valid, generated_by_anchor = build_catalog(rng, args.limit, args.rows_per_anchor, deadline)
    rows, nodes, best_depth, best_gaps, catalog_size, best_trace = search_catalog(
        catalog, args.limit, deadline, args.node_limit, args.anchor_probe, rng
    )
    checked = verify(rows) if rows is not None else {"valid": False, "scope": None}
    payload = {
        "method": "targeted-difference-allocation-catalog-exact-cover",
        "limit": args.limit,
        "rows_per_anchor": args.rows_per_anchor,
        "anchor_order": "descending difference; row generation conditional on anchor",
        "anchor_probe": args.anchor_probe,
        "seconds": args.seconds,
        "node_limit": args.node_limit,
        "seed": args.seed,
        "catalog_size": catalog_size,
        "generation_attempts": attempts,
        "valid_generated_rows": valid,
        "generated_by_anchor": generated_by_anchor,
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
    print(json.dumps({"target_reached": payload["target_reached"], "catalog_size": catalog_size, "search_nodes": nodes, "best_depth": best_depth, "best_gaps": best_gaps, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
