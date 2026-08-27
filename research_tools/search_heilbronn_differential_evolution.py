#!/usr/bin/env python3
"""NumPy-only global differential-evolution search for Heilbronn n=12.

This search deliberately uses the source-faithful Comellas--Yebra point
coordinates as one elite seed, but evaluates the full absolute-determinant
objective without fixing triangle orientations.  The script is exploratory:
the decimal output must be checked independently before any comparison claim.
"""

from __future__ import annotations

import argparse
import json
import time
from itertools import combinations
from pathlib import Path

import numpy as np


TRIPLES = np.asarray(list(combinations(range(12), 3)), dtype=np.int64)


def minimum_areas(population: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return the minimum area and its triangle index for every population row."""
    points = population.reshape((-1, 12, 2))
    p_i = points[:, TRIPLES[:, 0], :]
    p_j = points[:, TRIPLES[:, 1], :]
    p_k = points[:, TRIPLES[:, 2], :]
    determinants = (
        (p_j[:, :, 0] - p_i[:, :, 0]) * (p_k[:, :, 1] - p_i[:, :, 1])
        - (p_k[:, :, 0] - p_i[:, :, 0]) * (p_j[:, :, 1] - p_i[:, :, 1])
    )
    areas = np.abs(determinants) / 2.0
    indices = np.argmin(areas, axis=1)
    return areas[np.arange(len(population)), indices], indices


def initialize_population(
    baseline: np.ndarray, population_size: int, rng: np.random.Generator
) -> np.ndarray:
    population = rng.random((population_size, baseline.size))
    population[0] = baseline.reshape(-1)
    half = max(1, (population_size - 1) // 2)
    scales = rng.choice([0.002, 0.005, 0.012, 0.03], size=half)
    for index, scale in enumerate(scales, start=1):
        population[index] = np.clip(
            baseline.reshape(-1) + rng.normal(0.0, scale, baseline.size), 0.0, 1.0
        )
    return population


def run(
    baseline: np.ndarray,
    seed: int,
    population_size: int,
    generations: int,
    polish_steps: int,
) -> dict[str, object]:
    rng = np.random.default_rng(seed)
    started = time.monotonic()
    population = initialize_population(baseline, population_size, rng)
    scores, triangles = minimum_areas(population)
    best_index = int(np.argmax(scores))
    best = population[best_index].copy()
    best_score = float(scores[best_index])
    best_triangle = int(triangles[best_index])
    generation_best: list[float] = [best_score]

    for _generation in range(generations):
        choices = np.empty((population_size, 3), dtype=np.int64)
        for target in range(population_size):
            available = np.delete(np.arange(population_size), target)
            choices[target] = rng.choice(available, size=3, replace=False)
        differential = population[choices[:, 0]] + 0.8 * (
            population[choices[:, 1]] - population[choices[:, 2]]
        )
        crossover = rng.random((population_size, baseline.size)) < 0.9
        crossover[np.arange(population_size), rng.integers(0, baseline.size, population_size)] = True
        trials = np.where(crossover, differential, population)
        trials = np.clip(trials, 0.0, 1.0)
        trial_scores, trial_triangles = minimum_areas(trials)
        replace = trial_scores >= scores
        population[replace] = trials[replace]
        scores[replace] = trial_scores[replace]
        triangles[replace] = trial_triangles[replace]
        current_index = int(np.argmax(scores))
        if float(scores[current_index]) > best_score:
            best = population[current_index].copy()
            best_score = float(scores[current_index])
            best_triangle = int(triangles[current_index])
        # Retain the best point even if it was selected as a trial target.
        worst_index = int(np.argmin(scores))
        population[worst_index] = best
        scores[worst_index] = best_score
        triangles[worst_index] = best_triangle
        generation_best.append(best_score)

    # A bounded, mutation-only basin polish complements the global DE phase.
    for scale in (0.02, 0.01, 0.005, 0.002, 0.001, 0.0005, 0.0002):
        remaining = polish_steps // 7
        for _step in range(remaining):
            proposal = np.clip(best + rng.normal(0.0, scale, best.size), 0.0, 1.0)
            score, triangle = minimum_areas(proposal[None, :])
            if float(score[0]) > best_score:
                best = proposal
                best_score = float(score[0])
                best_triangle = int(triangle[0])

    return {
        "seed": seed,
        "population_size": population_size,
        "generations": generations,
        "polish_steps": polish_steps,
        "best_minimum_area_float64": best_score,
        "best_minimum_triangle": list(map(int, TRIPLES[best_triangle])),
        "points": best.reshape((12, 2)).tolist(),
        "generation_best_tail": generation_best[-20:],
        "elapsed_seconds": time.monotonic() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--population-size", type=int, default=96)
    parser.add_argument("--generations", type=int, default=1500)
    parser.add_argument("--polish-steps", type=int, default=7000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline_payload = json.loads(args.baseline.read_text(encoding="utf-8"))
    baseline = np.asarray([[float(x), float(y)] for x, y in baseline_payload["points"]], dtype=float)
    baseline_minimum = float(minimum_areas(baseline.reshape(1, -1))[0][0])
    runs = [
        run(baseline, seed, args.population_size, args.generations, args.polish_steps)
        for seed in args.seed
    ]
    best = max(runs, key=lambda item: float(item["best_minimum_area_float64"]))
    payload = {
        "method": "numpy-differential-evolution-full-absolute-triangle-objective",
        "baseline_minimum_area_float64": baseline_minimum,
        "runs": runs,
        "best_run": best,
        "best_minimum_area_float64": best["best_minimum_area_float64"],
        "improvement_over_float_baseline": float(best["best_minimum_area_float64"]) - baseline_minimum,
        "certification_status": "not_certified_float_search_only",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "best_minimum_area_float64": payload["best_minimum_area_float64"],
        "improvement": payload["improvement_over_float_baseline"],
        "output": str(args.output),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
