#!/usr/bin/env python3
"""Best-response packing of a valid scope-111 Golomb-ruler library."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

from verify_dts import verify


ROW_SIZE = 6


def make_row(rng: random.Random, limit: int) -> tuple[int, list[int]] | None:
    row = [0] + sorted(rng.sample(range(1, limit + 1), ROW_SIZE - 1))
    differences = [row[right] - row[left] for left in range(ROW_SIZE) for right in range(left + 1, ROW_SIZE)]
    if len(set(differences)) != 15:
        return None
    return sum(1 << difference for difference in differences), row


def build_library(
    rng: random.Random,
    limit: int,
    target_size: int,
    attempt_limit: int,
    deadline: float,
) -> tuple[list[tuple[int, list[int]]], int, int]:
    library: dict[int, list[int]] = {}
    attempts = 0
    valid = 0
    while len(library) < target_size and attempts < attempt_limit and time.monotonic() < deadline:
        attempts += 1
        candidate = make_row(rng, limit)
        if candidate is None:
            continue
        valid += 1
        library.setdefault(candidate[0], candidate[1])
    return list(library.items()), attempts, valid


def pack_library(
    library: list[tuple[int, list[int]]],
    limit: int,
    deadline: float,
    rng: random.Random,
    sample_size: int,
    anchor_trials: int,
    restart_after: int,
) -> tuple[list[list[int]], int, int, int, int]:
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

    def best_replacement(indices: list[int], position: int) -> tuple[int, int]:
        other_mask = union_mask(indices[:position] + indices[position + 1 :])
        candidates: set[int] = set()
        pool_size = len(library)
        for _ in range(sample_size):
            candidates.add(rng.randrange(pool_size))
        uncovered = [difference for difference in range(1, limit + 1) if not (other_mask & (1 << difference))]
        rng.shuffle(uncovered)
        for difference in uncovered[: min(16, len(uncovered))]:
            options = by_difference[difference]
            for _ in range(min(anchor_trials, len(options))):
                candidates.add(options[rng.randrange(len(options))])
        best_index = indices[position]
        best_score = (other_mask | library[best_index][0]).bit_count()
        for candidate_index in candidates:
            score = (other_mask | library[candidate_index][0]).bit_count()
            if score > best_score or (score == best_score and rng.random() < 0.05):
                best_index = candidate_index
                best_score = score
        return best_index, best_score

    def initialize() -> list[int]:
        indices = [rng.randrange(len(library))]
        while len(indices) < 7 and time.monotonic() < deadline:
            position = len(indices)
            candidates = [rng.randrange(len(library)) for _ in range(sample_size)]
            used = union_mask(indices)
            best_index = max(candidates, key=lambda index: (used | library[index][0]).bit_count())
            indices.append(best_index)
        while len(indices) < 7:
            indices.append(rng.randrange(len(library)))
        return indices

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
            best_indices = current[:]
            best_score = current_score
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
        position = rng.randrange(7)
        candidate_index, candidate_score = best_replacement(current, position)
        delta = candidate_score - current_score
        temperature = 0.25
        if delta >= 0 or rng.random() < math.exp(delta / temperature):
            current[position] = candidate_index
            current_score = candidate_score

    rows = [library[index][1][:] for index in best_indices]
    return rows, best_score, iterations, restarts, len(best_indices)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--library-size", type=int, default=100000)
    parser.add_argument("--attempt-limit", type=int, default=500000)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument("--sample-size", type=int, default=400)
    parser.add_argument("--anchor-trials", type=int, default=80)
    parser.add_argument("--restart-after", type=int, default=700)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    deadline = started + args.seconds
    rng = random.Random(args.seed)
    library, attempts, valid = build_library(rng, args.limit, args.library_size, args.attempt_limit, deadline)
    rows, best_unique, iterations, restarts, selected_count = pack_library(
        library, args.limit, deadline, rng, args.sample_size, args.anchor_trials, args.restart_after
    )
    checked = verify(rows) if selected_count == 7 else {"valid": False, "scope": None}
    payload = {
        "method": "valid-golomb-ruler-library-best-response-packing",
        "limit": args.limit,
        "library_size_target": args.library_size,
        "library_size": len(library),
        "generation_attempt_limit": args.attempt_limit,
        "generation_attempts": attempts,
        "valid_generated_rows": valid,
        "seconds": args.seconds,
        "seed": args.seed,
        "sample_size": args.sample_size,
        "anchor_trials": args.anchor_trials,
        "restart_after": args.restart_after,
        "packing_iterations": iterations,
        "restarts": restarts,
        "best_unique_difference_count": best_unique,
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
