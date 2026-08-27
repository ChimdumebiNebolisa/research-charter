#!/usr/bin/env python3
"""Conflict-directed row-library swaps for scope-111 DTS packing."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

from search_dts_library_packing import build_library
from verify_dts import verify


def search(
    library: list[tuple[int, list[int]]],
    limit: int,
    deadline: float,
    rng: random.Random,
    candidate_trials: int,
    restart_after: int,
) -> tuple[list[list[int]], int, int, int, list[int]]:
    by_difference: list[list[int]] = [[] for _ in range(limit + 1)]
    for index, (mask, _row) in enumerate(library):
        for difference in range(1, limit + 1):
            if mask & (1 << difference):
                by_difference[difference].append(index)

    def union_mask(indices: list[int]) -> int:
        result = 0
        for index in indices:
            result |= library[index][0]
        return result

    def initialize() -> list[int]:
        indices = [rng.randrange(len(library))]
        while len(indices) < 7 and time.monotonic() < deadline:
            used = union_mask(indices)
            sample = [rng.randrange(len(library)) for _ in range(500)]
            indices.append(max(sample, key=lambda index: (used | library[index][0]).bit_count()))
        while len(indices) < 7:
            indices.append(rng.randrange(len(library)))
        return indices

    def counts(indices: list[int]) -> list[int]:
        result = [0] * (limit + 1)
        for index in indices:
            mask = library[index][0]
            for difference in range(1, limit + 1):
                if mask & (1 << difference):
                    result[difference] += 1
        return result

    best_indices: list[int] = []
    best_score = 0
    iterations = 0
    restarts = 0
    stagnant = 0
    current = initialize()
    current_score = union_mask(current).bit_count()
    while time.monotonic() < deadline:
        iterations += 1
        if current_score > best_score:
            best_score = current_score
            best_indices = current[:]
            stagnant = 0
        else:
            stagnant += 1
        if best_score == 105:
            break
        if stagnant >= restart_after:
            restarts += 1
            current = initialize()
            current_score = union_mask(current).bit_count()
            stagnant = 0
            continue

        current_counts = counts(current)
        duplicates = [difference for difference in range(1, limit + 1) if current_counts[difference] > 1]
        missing = [difference for difference in range(1, limit + 1) if current_counts[difference] == 0]
        if not duplicates or not missing:
            continue
        duplicate = rng.choice(duplicates)
        positions = [position for position, index in enumerate(current) if library[index][0] & (1 << duplicate)]
        position = rng.choice(positions)
        other_mask = union_mask(current[:position] + current[position + 1 :])
        candidate_indices: set[int] = set()
        rng.shuffle(missing)
        for difference in missing[: min(20, len(missing))]:
            options = by_difference[difference]
            for _ in range(min(candidate_trials, len(options))):
                candidate_indices.add(options[rng.randrange(len(options))])
        candidate_indices.update(rng.randrange(len(library)) for _ in range(candidate_trials))
        scored = []
        for candidate_index in candidate_indices:
            candidate_mask = library[candidate_index][0]
            overlap = (candidate_mask & other_mask).bit_count()
            new_score = (candidate_mask | other_mask).bit_count()
            scored.append((overlap, -new_score, rng.random(), candidate_index, new_score))
        if not scored:
            continue
        overlap, _negative_score, _tie, candidate_index, candidate_score = min(scored)
        delta = candidate_score - current_score
        if delta >= 0 or (overlap <= 7 and rng.random() < math.exp(delta / 0.5)):
            current[position] = candidate_index
            current_score = candidate_score

    rows = [library[index][1][:] for index in best_indices]
    return rows, best_score, iterations, restarts, [difference for difference in range(1, limit + 1) if union_mask(best_indices) & (1 << difference)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--library-size", type=int, default=100000)
    parser.add_argument("--attempt-limit", type=int, default=500000)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=20260901)
    parser.add_argument("--candidate-trials", type=int, default=120)
    parser.add_argument("--restart-after", type=int, default=500)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    deadline = started + args.seconds
    rng = random.Random(args.seed)
    library, attempts, valid = build_library(rng, args.limit, args.library_size, args.attempt_limit, deadline)
    rows, best_unique, iterations, restarts, covered = search(
        library, args.limit, deadline, rng, args.candidate_trials, args.restart_after
    )
    checked = verify(rows) if len(rows) == 7 else {"valid": False, "scope": None}
    payload = {
        "method": "conflict-directed-valid-row-library-swaps",
        "limit": args.limit,
        "library_size_target": args.library_size,
        "library_size": len(library),
        "generation_attempt_limit": args.attempt_limit,
        "generation_attempts": attempts,
        "valid_generated_rows": valid,
        "seconds": args.seconds,
        "seed": args.seed,
        "candidate_trials": args.candidate_trials,
        "restart_after": args.restart_after,
        "packing_iterations": iterations,
        "restarts": restarts,
        "best_unique_difference_count": best_unique,
        "covered_differences": covered,
        "rows": rows,
        "verification": checked,
        "target_reached": bool(checked["valid"] and checked["scope"] <= args.limit),
        "elapsed_seconds": time.monotonic() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_reached": payload["target_reached"], "library_size": len(library), "best_unique": best_unique, "iterations": iterations, "restarts": restarts, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
