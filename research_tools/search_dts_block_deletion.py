#!/usr/bin/env python3
"""Upstream-inspired reversible block-deletion search for a (7,5)-DTS."""

from __future__ import annotations

import argparse
import json
import random
import statistics
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
    if len(row) != 6 or row[0] != 0 or row[-1] > limit:
        return None
    if any(left >= right for left, right in zip(row, row[1:])):
        return None
    differences = [row[right] - row[left] for right in range(1, 6) for left in range(right)]
    if len(set(differences)) != 15:
        return None
    return sum(1 << difference for difference in differences)


def profile() -> tuple[list[float], list[float]]:
    """Estimate normalized mark positions from the published scope-112 witness."""
    columns = [[row[index] / 112.0 for row in START_ROWS] for index in range(1, 6)]
    means = [statistics.fmean(column) for column in columns]
    sigmas = [statistics.pstdev(column) for column in columns]
    return means, sigmas


def sample_mark(
    rng: random.Random,
    position: int,
    previous: int,
    limit: int,
    means: list[float],
    sigmas: list[float],
) -> int:
    remaining = 5 - position
    minimum = previous + 1
    maximum = limit - remaining
    if rng.random() < 0.25:
        return rng.randint(minimum, maximum)
    proposed = round(limit * (means[position - 1] + sigmas[position - 1] * rng.gauss(0.0, 1.0)))
    return max(minimum, min(maximum, proposed))


def build_row(
    rng: random.Random,
    used: int,
    limit: int,
    mark_attempts: int,
    means: list[float],
    sigmas: list[float],
) -> tuple[list[int], int] | None:
    marks = [0]
    local_mask = 0
    for position in range(1, 6):
        accepted = False
        for _ in range(mark_attempts):
            mark = sample_mark(rng, position, marks[-1], limit, means, sigmas)
            updates = [mark - prior for prior in marks]
            update_mask = sum(1 << difference for difference in updates)
            if len(set(updates)) == len(updates) and not update_mask & local_mask and not update_mask & used:
                marks.append(mark)
                local_mask |= update_mask
                accepted = True
                break
        if not accepted:
            return None
    return marks, local_mask


def rebuild(rows: list[tuple[list[int], int]]) -> int:
    used = 0
    for _row, mask in rows:
        used |= mask
    return used


def run(seed: int, seconds: float, limit: int, mark_attempts: int) -> dict[str, object]:
    rng = random.Random(seed)
    means, sigmas = profile()
    deadline = time.monotonic() + seconds
    rows: list[tuple[list[int], int]] = []
    used = 0
    best_rows: list[list[int]] = []
    best_depth = 0
    best_unique = 0
    best_scope: int | None = None
    full_trials = 0
    generation_failures = 0
    deletions = 0
    replacements = 0
    restarts = 0

    while time.monotonic() < deadline:
        if len(rows) == 7:
            full_trials += 1
            candidate = [row[:] for row, _mask in rows]
            checked = verify(candidate)
            if checked["valid"] and checked["scope"] <= limit:
                return {
                    "seed": seed,
                    "target_reached": True,
                    "best_rows": candidate,
                    "best_depth": 7,
                    "best_unique_difference_count": 105,
                    "best_scope": checked["scope"],
                    "full_trials": full_trials,
                    "generation_failures": generation_failures,
                    "deletions": deletions,
                    "replacements": replacements,
                    "restarts": restarts,
                    "verification": checked,
                }
            rows = []
            used = 0
            restarts += 1
            continue

        generated = build_row(rng, used, limit, mark_attempts, means, sigmas)
        if generated is not None:
            rows.append(generated)
            used |= generated[1]
            current_depth = len(rows)
            if (current_depth, used.bit_count()) > (best_depth, best_unique):
                best_depth = current_depth
                best_unique = used.bit_count()
                best_rows = [row[:] for row, _mask in rows]
                best_scope = max(row[-1] for row, _mask in rows)
            continue

        generation_failures += 1
        if not rows:
            restarts += 1
            continue

        # The pinned upstream search deletes an earlier block and tries to
        # generate a replacement against the remaining cumulative spectrum.
        indices = list(range(len(rows)))
        rng.shuffle(indices)
        replaced = False
        for index in indices:
            kept = rows[:index] + rows[index + 1 :]
            kept_mask = rebuild(kept)
            replacement = build_row(rng, kept_mask, limit, mark_attempts, means, sigmas)
            deletions += 1
            if replacement is not None:
                rows = kept + [replacement]
                used = kept_mask | replacement[1]
                replacements += 1
                replaced = True
                break
        if not replaced:
            rows = rows[:-1]
            used = rebuild(rows)
            restarts += 1

    checked = verify(best_rows) if len(best_rows) == 7 else {"valid": False, "scope": best_scope}
    return {
        "seed": seed,
        "target_reached": False,
        "best_rows": best_rows,
        "best_depth": best_depth,
        "best_unique_difference_count": best_unique,
        "best_scope": best_scope,
        "full_trials": full_trials,
        "generation_failures": generation_failures,
        "deletions": deletions,
        "replacements": replacements,
        "restarts": restarts,
        "verification": checked,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--seconds-per-seed", type=float, default=20.0)
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--mark-attempts", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runs = [run(seed, args.seconds_per_seed, args.limit, args.mark_attempts) for seed in args.seed]
    best = max(runs, key=lambda item: (item["target_reached"], item["best_depth"], item["best_unique_difference_count"]))
    payload = {
        "method": "upstream-inspired-sequential-bitmask-generation-with-block-deletion",
        "limit": args.limit,
        "mark_attempts": args.mark_attempts,
        "seconds_per_seed": args.seconds_per_seed,
        "runs": runs,
        "best_run": best,
        "target_reached": bool(best["target_reached"]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_reached": payload["target_reached"], "best_depth": best["best_depth"], "best_unique": best["best_unique_difference_count"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
