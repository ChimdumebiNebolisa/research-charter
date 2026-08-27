#!/usr/bin/env python3
"""Search a coordinated quadratic-gap family for a scope-111 DTS."""

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


def rows_from_parameters(c: list[int], t: list[int], q: list[int]) -> list[list[int]]:
    rows: list[list[int]] = []
    for row_index in range(ROWS):
        row = [0]
        for gap_index in range(GAPS):
            gap = c[gap_index] + row_index * t[gap_index] + (row_index * (row_index - 1) // 2) * q[gap_index]
            row.append(row[-1] + gap)
        rows.append(row)
    return rows


def evaluate(c: list[int], t: list[int], q: list[int], limit: int) -> tuple[float, int, int, int, int]:
    rows = rows_from_parameters(c, t, q)
    gaps = [
        c[j] + row_index * t[j] + (row_index * (row_index - 1) // 2) * q[j]
        for row_index in range(ROWS)
        for j in range(GAPS)
    ]
    overflow = sum(max(0, row[-1] - limit) for row in rows)
    invalid_gaps = sum(max(0, 1 - gap) for gap in gaps)
    local_collisions = 0
    differences: list[int] = []
    for row in rows:
        row_differences = [row[right] - row[left] for left in range(6) for right in range(left + 1, 6)]
        differences.extend(row_differences)
        local_collisions += 15 - len(set(row_differences))
    unique = len(set(differences))
    objective = unique - 100.0 * invalid_gaps - 10.0 * overflow - 10.0 * local_collisions
    return objective, unique, invalid_gaps, overflow, local_collisions


def random_feasible(rng: random.Random, limit: int) -> tuple[list[int], list[int], list[int]]:
    while True:
        c = [rng.randint(8, 30) for _ in range(GAPS)]
        t = [rng.randint(-8, 8) for _ in range(GAPS)]
        q = [rng.randint(-2, 2) for _ in range(GAPS)]
        score = evaluate(c, t, q, limit)
        if score[2] == 0 and score[3] == 0:
            return c, t, q


def run(seed: int, seconds: float, limit: int) -> dict[str, object]:
    rng = random.Random(seed)
    deadline = time.monotonic() + seconds
    c, t, q = random_feasible(rng, limit)
    current = evaluate(c, t, q, limit)
    best_c, best_t, best_q = c[:], t[:], q[:]
    best = current
    iterations = 0
    accepted = 0
    restarts = 0
    while time.monotonic() < deadline:
        iterations += 1
        if rng.random() < 0.03:
            candidate_c, candidate_t, candidate_q = random_feasible(rng, limit)
            restarts += 1
        else:
            candidate_c, candidate_t, candidate_q = c[:], t[:], q[:]
            count = 1 if rng.random() < 0.85 else 2
            for _ in range(count):
                target = rng.choice([candidate_c, candidate_t, candidate_q])
                index = rng.randrange(GAPS)
                target[index] += rng.choice([-2, -1, 1, 2])
        candidate_score = evaluate(candidate_c, candidate_t, candidate_q, limit)
        progress = max(0.01, (deadline - time.monotonic()) / seconds)
        temperature = max(0.15, 2.5 * progress)
        delta = candidate_score[0] - current[0]
        if delta >= 0 or rng.random() < math.exp(delta / temperature):
            c, t, q, current = candidate_c, candidate_t, candidate_q, candidate_score
            accepted += 1
        if current > best:
            best_c, best_t, best_q, best = c[:], t[:], q[:], current
        rows = rows_from_parameters(best_c, best_t, best_q)
        checked = verify(rows)
        if checked["valid"] and checked["scope"] <= limit:
            return {
                "seed": seed,
                "target_reached": True,
                "iterations": iterations,
                "accepted": accepted,
                "restarts": restarts,
                "parameters": {"c": best_c, "t": best_t, "q": best_q},
                "best_score": best,
                "rows": rows,
                "verification": checked,
            }
    rows = rows_from_parameters(best_c, best_t, best_q)
    return {
        "seed": seed,
        "target_reached": False,
        "iterations": iterations,
        "accepted": accepted,
        "restarts": restarts,
        "parameters": {"c": best_c, "t": best_t, "q": best_q},
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
        "method": "coordinated-quadratic-consecutive-gap-search",
        "limit": args.limit,
        "seeds": args.seed,
        "seconds_per_seed": args.seconds_per_seed,
        "parameterization": "gap[j](row)=c[j]+row*t[j]+binomial(row,2)*q[j], rows indexed 0..6",
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
