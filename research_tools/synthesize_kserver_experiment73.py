"""Bounded CEGIS synthesis for the preregistered Experiment 73 grammar.

Candidates are functions of work-function features only.  Metric edge indices
are used exclusively as active constraints/counterexamples; they are never
available to the candidate expression.
"""

from __future__ import annotations

import itertools
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "artifacts" / "upstream-cache" / "k-server-bench"
sys.path.insert(0, str(UPSTREAM / "k-servers" / "src"))
sys.path.insert(0, str(ROOT / "research_tools" / "compat"))

from kserver.evaluation import NumpyKServerInstance
from kserver.potential.canonical_potential import Potential as CanonicalPotential


INDEX_MATRIX = [
    [-5, -5, -5, -5],
    [5, -1, -2, -2],
    [5, 1, 3, 4],
    [5, 2, -4, -4],
    [5, 2, 4, -3],
]
COEFS = [-1, 0, -1, 0, 1, 0, 0, -1, 0, 0]
FEATURE_NAMES = ["wf_mean_centered", "wf_max_centered", "wf_std_centered"]
FEATURE_GRID = (-1.0, -0.5, 0.0, 0.5, 1.0)
BRANCH_GRID = tuple(itertools.product(FEATURE_GRID, repeat=4))
MODES = ("max", "min")
METRIC_DIR = UPSTREAM / "metrics"
TAXI_CACHE = ROOT / "artifacts" / "kserver-experiment73-teacher-cache.npz"
OUTPUT = ROOT / "artifacts" / "kserver-experiment73-synthesis.json"


@dataclass
class MetricData:
    name: str
    instance: NumpyKServerInstance
    base: np.ndarray
    features: np.ndarray


def make_features(wfs: np.ndarray) -> np.ndarray:
    return np.column_stack([
        np.mean(wfs, axis=1) - 4.0,
        np.max(wfs, axis=1) - 7.0,
        np.std(wfs, axis=1) - 1.5,
    ])


def canonical_values(instance: NumpyKServerInstance, cached: np.ndarray | None = None) -> np.ndarray:
    if cached is not None and len(cached) == len(instance.node_id):
        return np.asarray(cached, dtype=float)
    potential = CanonicalPotential(instance.get_context(), n=5, index_matrix=INDEX_MATRIX, coefs=COEFS)
    values = np.empty(len(instance.node_id), dtype=float)
    for index, row in enumerate(instance.node_wf_norm):
        values[index] = float(potential(row)[0])
    return values


def load_metric(name: str, cached: np.ndarray | None = None) -> MetricData:
    instance = NumpyKServerInstance.load(METRIC_DIR / name)
    return MetricData(name, instance, canonical_values(instance, cached), make_features(instance.node_wf_norm))


def correction(features: np.ndarray, mode: str, branches: tuple[tuple[float, ...], ...]) -> np.ndarray:
    values = np.column_stack([
        branch[0] + features @ np.asarray(branch[1:], dtype=float) for branch in branches
    ])
    values = np.column_stack([np.zeros(len(features)), values])
    return np.max(values, axis=1) if mode == "max" else np.min(values, axis=1)


def potential_values(metric: MetricData, mode: str, branches: tuple[tuple[float, ...], ...]) -> np.ndarray:
    return metric.base + correction(metric.features, mode, branches)


def edge_weight(metric: MetricData) -> np.ndarray:
    instance = metric.instance
    return np.rint(instance.edge_ext - (instance.k + 1) * instance.edge_d_min).astype(float)


def edge_slack(metric: MetricData, values: np.ndarray, indexes: np.ndarray | None = None) -> np.ndarray:
    instance = metric.instance
    weights = edge_weight(metric)
    slack = values[instance.edge_to] - values[instance.edge_from] - weights
    return slack if indexes is None else slack[indexes]


def active_arrays(active: dict[str, set[int]], metrics: dict[str, MetricData]):
    rows = []
    for name, indexes in active.items():
        metric = metrics[name]
        edge_indexes = np.asarray(sorted(indexes), dtype=int)
        rows.append((name, edge_indexes, metric.base[metric.instance.edge_to[edge_indexes]] - metric.base[metric.instance.edge_from[edge_indexes]] - edge_weight(metric)[edge_indexes], metric.features[metric.instance.edge_from[edge_indexes]], metric.features[metric.instance.edge_to[edge_indexes]]))
    return rows


def score_active(active: dict[str, set[int]], metrics: dict[str, MetricData], mode: str, branches: tuple[tuple[float, ...], ...]) -> tuple[float, float]:
    minimum = float("inf")
    negative_sum = 0.0
    for name, edge_indexes, base_slack, from_features, to_features in active_arrays(active, metrics):
        from_correction = correction(from_features, mode, branches)
        to_correction = correction(to_features, mode, branches)
        slack = base_slack + to_correction - from_correction
        minimum = min(minimum, float(np.min(slack)))
        negative_sum += float(np.sum(np.minimum(slack, 0.0)))
    return minimum, negative_sum


def best_single(active, metrics, mode):
    scored = [(score_active(active, metrics, mode, (branch,)), branch) for branch in BRANCH_GRID]
    return max(scored, key=lambda item: (item[0][0], item[0][1]))[1]


def top_singles(active, metrics, mode, count):
    scored = [(score_active(active, metrics, mode, (branch,)), branch) for branch in BRANCH_GRID]
    scored.sort(reverse=True, key=lambda item: (item[0][0], item[0][1]))
    return [branch for _score, branch in scored[:count]]


def best_multi(active, metrics, mode, branch_count, pool_count):
    pool = top_singles(active, metrics, mode, pool_count)
    best = None
    for branches in itertools.combinations(pool, branch_count):
        score = score_active(active, metrics, mode, branches)
        if best is None or (score[0], score[1]) > (best[0][0], best[0][1]):
            best = (score, branches)
    assert best is not None
    return best[1]


def audit(metric: MetricData, values: np.ndarray) -> dict[str, object]:
    slack = edge_slack(metric, values)
    violated = np.flatnonzero(slack < 0)
    return {
        "metric": metric.name,
        "nodes": int(len(metric.instance.node_id)),
        "edges": int(len(slack)),
        "violations": int(len(violated)),
        "first_violated_edges": [int(i) for i in violated[:100]],
        "min_slack": float(np.min(slack)),
        "potential_min": float(np.min(values)),
        "potential_max": float(np.max(values)),
    }


def main() -> int:
    started = time.time()
    cache = np.load(TAXI_CACHE)
    taxi = load_metric("circle_taxi_k4_m6.pickle", cache["canonical"])
    circle = load_metric("circle_k4_m6.pickle")
    metrics = {taxi.name: taxi, circle.name: circle}
    taxi_slack = edge_slack(taxi, taxi.base)
    circle_slack = edge_slack(circle, circle.base)
    active = {
        taxi.name: set([4766035, 5594108, 6193322]) | set(np.argsort(taxi_slack)[:128].tolist()),
        circle.name: set(range(len(circle_slack))),
    }
    trajectory = []
    final_candidate = None
    for branch_count, pool_count in ((1, 0), (2, 32), (3, 24)):
        for mode in MODES:
            for iteration in range(4):
                if branch_count == 1:
                    branches = (best_single(active, metrics, mode),)
                else:
                    branches = best_multi(active, metrics, mode, branch_count, pool_count)
                values = {name: potential_values(metric, mode, branches) for name, metric in metrics.items()}
                audits = {name: audit(metric, values[name]) for name, metric in metrics.items()}
                trajectory.append({
                    "complexity": f"{branch_count + 1}-piece_{mode}",
                    "iteration": iteration,
                    "branches": [list(branch) for branch in branches],
                    "active_min_slack": score_active(active, metrics, mode, branches)[0],
                    "audits": audits,
                })
                new_edges = set(audits[taxi.name]["first_violated_edges"]) | set(audits[circle.name]["first_violated_edges"])
                if not new_edges:
                    final_candidate = {"mode": mode, "branches": branches, "values": values, "audits": audits, "complexity": f"{branch_count + 1}-piece_{mode}"}
                    break
                before = sum(len(value) for value in active.values())
                active[taxi.name].update(audits[taxi.name]["first_violated_edges"])
                active[circle.name].update(audits[circle.name]["first_violated_edges"])
                after = sum(len(value) for value in active.values())
                if after == before:
                    break
            if final_candidate is not None and final_candidate["audits"][taxi.name]["violations"] < 3 and final_candidate["audits"][circle.name]["violations"] == 0:
                break
        if final_candidate is not None and final_candidate["audits"][taxi.name]["violations"] < 3 and final_candidate["audits"][circle.name]["violations"] == 0:
            break
    result = {
        "status": "completed",
        "grammar": {
            "base": "published canonical n=5 potential",
            "features": FEATURE_NAMES,
            "feature_centers": {"wf_mean": 4.0, "wf_max": 7.0, "wf_std": 1.5},
            "coefficient_grid": list(FEATURE_GRID),
            "piece_hierarchy": ["max/min of 0 and one affine branch", "max/min of 0 and two affine branches", "max/min of 0 and three affine branches"],
        },
        "active_set_initialization": {name: len(indexes) for name, indexes in active.items()},
        "trajectory": trajectory,
        "final_candidate": None if final_candidate is None else {key: value for key, value in final_candidate.items() if key != "values"},
        "elapsed_seconds": time.time() - started,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    print(OUTPUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
