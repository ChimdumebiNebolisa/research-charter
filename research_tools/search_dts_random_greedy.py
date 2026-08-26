#!/usr/bin/env python3
"""From-scratch randomized greedy search for disjoint Golomb rulers."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from verify_dts import verify


def random_row(rng: random.Random, limit: int) -> tuple[list[int], set[int]] | None:
    row = [0] + sorted(rng.sample(range(1, limit + 1), 5))
    differences = [row[j] - row[i] for i in range(6) for j in range(i + 1, 6)]
    if len(set(differences)) != 15:
        return None
    return row, set(differences)


def run(seed: int, seconds: float, limit: int, pool_per_level: int) -> dict[str, object]:
    rng = random.Random(seed)
    deadline = time.monotonic() + seconds
    best_rows: list[list[int]] = []
    best_unique = 0
    attempts = 0
    restarts = 0
    while time.monotonic() < deadline:
        restarts += 1
        rows: list[list[int]] = []
        used: set[int] = set()
        for _level in range(7):
            candidates: list[tuple[list[int], set[int]]] = []
            for _ in range(pool_per_level):
                attempts += 1
                candidate = random_row(rng, limit)
                if candidate is not None and not candidate[1] & used:
                    candidates.append(candidate)
            if not candidates:
                break
            # Favor large span rows early only as a tie-breaker; the primary
            # criterion is compatibility with already selected differences.
            row, differences = max(candidates, key=lambda item: (len(item[1] - used), item[0][-1], rng.random()))
            rows.append(row)
            used.update(differences)
            if len(rows) > len(best_rows):
                best_rows = [item[:] for item in rows]
                best_unique = len(used)
        if len(rows) == 7:
            checked = verify(rows)
            if checked["valid"] and checked["scope"] <= limit:
                return {"seed": seed, "attempts": attempts, "restarts": restarts, "best_rows": rows, "best_unique": 105, "verification": checked, "target_reached": True}
    checked = verify(best_rows) if len(best_rows) == 7 else {"valid": False, "scope": max((row[-1] for row in best_rows), default=None)}
    return {"seed": seed, "attempts": attempts, "restarts": restarts, "best_rows": best_rows, "best_unique": best_unique, "verification": checked, "target_reached": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--seconds-per-seed", type=float, default=30.0)
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--pool-per-level", type=int, default=3000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runs = [run(seed, args.seconds_per_seed, args.limit, args.pool_per_level) for seed in args.seed]
    best = max(runs, key=lambda item: (item["target_reached"], len(item["best_rows"]), item["best_unique"]))
    payload = {
        "method": "from-scratch-randomized-greedy-disjoint-golomb-rulers",
        "limit": args.limit,
        "pool_per_level": args.pool_per_level,
        "seconds_per_seed": args.seconds_per_seed,
        "runs": runs,
        "best_run": best,
        "target_reached": bool(best["target_reached"]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_reached": payload["target_reached"], "best_unique": best["best_unique"], "rows": len(best["best_rows"]), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
