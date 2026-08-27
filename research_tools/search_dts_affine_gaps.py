#!/usr/bin/env python3
"""Search a coordinated affine-gap family for a scope-111 DTS."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

from verify_dts import verify


ROWS = 7
GAPS = 5


def rows_from_parameters(c: list[int], t: list[int]) -> list[list[int]]:
    rows: list[list[int]] = []
    for row_index in range(ROWS):
        row = [0]
        for gap_index in range(GAPS):
            row.append(row[-1] + c[gap_index] + row_index * t[gap_index])
        rows.append(row)
    return rows


def evaluate(c: list[int], t: list[int], limit: int) -> tuple[float, int, int, int, int]:
    rows = rows_from_parameters(c, t)
    gaps = [value for row_index in range(ROWS) for value in (c[j] + row_index * t[j] for j in range(GAPS))]
    overflow = sum(max(0, row[-1] - limit) for row in rows)
    invalid_gaps = sum(max(0, 1 - gap) for gap in gaps)
    differences = [
        row[right] - row[left]
        for row in rows
        for left in range(6)
        for right in range(left + 1, 6)
    ]
    unique = len(set(differences))
    local_collisions = sum(
        15 - len(
            {
                row[right] - row[left]
                for left in range(6)
                for right in range(left + 1, 6)
            }
        )
        for row in rows
    )
    objective = unique - 100.0 * invalid_gaps - 10.0 * overflow - 10.0 * local_collisions
    return objective, unique, invalid_gaps, overflow, local_collisions


def random_feasible(rng: random.Random, limit: int) -> tuple[list[int], list[int]]:
    while True:
        c = [rng.randint(8, 30) for _ in range(GAPS)]
        t = [rng.randint(-8, 8) for _ in range(GAPS)]
        if evaluate(c, t, limit)[2] == 0 and evaluate(c, t, limit)[3] == 0:
            return c, t


def run(seed: int, seconds: float, limit: int) -> dict[str, object]:
    rng = random.Random(seed)
    deadline = time.monotonic() + seconds
    c, t = random_feasible(rng, limit)
    current = evaluate(c, t, limit)
    best_c, best_t = c[:], t[:]
    best = current
    iterations = 0
    accepted = 0
    restarts = 0
    while time.monotonic() < deadline:
        iterations += 1
        if rng.random() < 0.03:
            candidate_c, candidate_t = random_feasible(rng, limit)
            restarts += 1
        else:
            candidate_c, candidate_t = c[:], t[:]
            count = 1 if rng.random() < 0.85 else 2
            for _ in range(count):
                target = candidate_c if rng.random() < 0.5 else candidate_t
                index = rng.randrange(GAPS)
                target[index] += rng.choice([-2, -1, 1, 2])
        candidate_score = evaluate(candidate_c, candidate_t, limit)
        progress = max(0.01, (deadline - time.monotonic()) / seconds)
        temperature = max(0.15, 2.5 * progress)
        delta = candidate_score[0] - current[0]
        if delta >= 0 or rng.random() < math.exp(delta / temperature):
            c, t, current = candidate_c, candidate_t, candidate_score
            accepted += 1
        if current > best:
            best_c, best_t, best = c[:], t[:], current
        rows = rows_from_parameters(best_c, best_t)
        checked = verify(rows)
        if checked["valid"] and checked["scope"] <= limit:
            return {
                "seed": seed,
                "target_reached": True,
                "iterations": iterations,
                "accepted": accepted,
                "restarts": restarts,
                "parameters": {"c": best_c, "t": best_t},
                "best_score": best,
                "rows": rows,
                "verification": checked,
            }
    rows = rows_from_parameters(best_c, best_t)
    return {
        "seed": seed,
        "target_reached": False,
        "iterations": iterations,
        "accepted": accepted,
        "restarts": restarts,
        "parameters": {"c": best_c, "t": best_t},
        "best_score": best,
        "rows": rows,
        "verification": verify(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--seconds-per-seed", type=float, default=40.0)
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    runs = [run(seed, args.seconds_per_seed, args.limit) for seed in args.seed]
    best = max(runs, key=lambda item: (item["target_reached"], item["best_score"]))
    payload = {
        "method": "coordinated-affine-consecutive-gap-search",
        "limit": args.limit,
        "seeds": args.seed,
        "seconds_per_seed": args.seconds_per_seed,
        "parameterization": "gap[j](row)=c[j]+row*t[j], rows indexed 0..6",
        "runs": runs,
        "best_run": best,
        "target_reached": bool(best["target_reached"]),
        "elapsed_seconds": time.monotonic() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "target_reached": payload["target_reached"],
                "best_score": best["best_score"],
                "best_unique": best["best_score"][1],
                "output": str(args.output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
