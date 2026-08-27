#!/usr/bin/env python3
"""Bounded local max-min search from the source-faithful Heilbronn baseline."""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


def determinant(points: np.ndarray, triple: tuple[int, int, int]) -> float:
    i, j, k = triple
    xi, yi = points[i]
    xj, yj = points[j]
    xk, yk = points[k]
    return float((xj - xi) * (yk - yi) - (xk - xi) * (yj - yi))


def minimum_area(points: np.ndarray, triples: list[tuple[int, int, int]]) -> tuple[float, tuple[int, int, int]]:
    values = [(abs(determinant(points, triple)) / 2.0, triple) for triple in triples]
    return min(values)


def run(points: np.ndarray, starts: int, seed: int, maxiter: int) -> dict[str, object]:
    triples = list(combinations(range(12), 3))
    signs = np.array([1.0 if determinant(points, triple) >= 0 else -1.0 for triple in triples])
    baseline_min, _ = minimum_area(points, triples)
    rng = np.random.default_rng(seed)
    candidates = [points.copy()]
    candidates.extend(np.clip(points + rng.normal(0.0, 0.005, size=points.shape), 0.0, 1.0) for _ in range(max(0, starts - 1)))
    runs = []

    def unpack(values: np.ndarray) -> np.ndarray:
        return values[:-1].reshape((12, 2))

    def constraints(values: np.ndarray) -> np.ndarray:
        candidate = unpack(values)
        t = values[-1]
        return np.array([sign * determinant(candidate, triple) / 2.0 - t for sign, triple in zip(signs, triples)])

    best_points = points.copy()
    best_area = baseline_min
    for index, start in enumerate(candidates):
        initial = np.concatenate([start.reshape(-1), [min(baseline_min * 0.95, baseline_min)]])
        result = minimize(
            lambda values: -values[-1],
            initial,
            method="SLSQP",
            bounds=[(0.0, 1.0)] * 24 + [(0.0, 0.5)],
            constraints={"type": "ineq", "fun": constraints},
            options={"maxiter": maxiter, "ftol": 1e-12, "disp": False},
        )
        candidate = unpack(result.x)
        area, triple = minimum_area(candidate, triples)
        runs.append({"start": index, "success": bool(result.success), "status": int(result.status), "message": str(result.message), "iterations": int(result.nit), "reported_t": float(result.x[-1]), "minimum_area_float64": area, "minimum_triangle": list(triple)})
        if area > best_area:
            best_area = area
            best_points = candidate.copy()

    payload = {
        "method": "source-faithful-heilbronn-slsqp-fixed-orientation-max-min",
        "points": [[format(float(x), ".17g"), format(float(y), ".17g")] for x, y in best_points],
        "baseline_minimum_area_float64": baseline_min,
        "best_minimum_area_float64": best_area,
        "improvement_over_float_baseline": best_area - baseline_min,
        "best_minimum_triangle": list(minimum_area(best_points, triples)[1]),
        "starts": starts,
        "seed": seed,
        "maxiter": maxiter,
        "runs": runs,
        "certification_status": "not_certified_float_search_only",
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--starts", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--maxiter", type=int, default=500)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    points = np.asarray([[float(x), float(y)] for x, y in baseline["points"]], dtype=float)
    payload = run(points, args.starts, args.seed, args.maxiter)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"best_minimum_area_float64": payload["best_minimum_area_float64"], "improvement": payload["improvement_over_float_baseline"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
