"""Bounded CEGIS synthesis for the preregistered Experiment 73 grammar.

Candidates are functions of work-function features only.  Metric edge indices
are used exclusively as active constraints/counterexamples; they are never
available to the candidate expression.
"""

from __future__ import annotations

import itertools
import json
import os
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
BRANCH_GRID_ARRAY = np.asarray(BRANCH_GRID, dtype=float)
MODES = ("max", "min")
METRIC_DIR = UPSTREAM / "metrics"
TAXI_CACHE = ROOT / "artifacts" / "kserver-experiment73-teacher-cache.npz"
OUTPUT = ROOT / "artifacts" / "kserver-experiment73-synthesis-resumed.json"
SCIENTIFIC_WALL_TIME = 900.0


@dataclass
class MetricData:
    name: str
    instance: NumpyKServerInstance
    base: np.ndarray
    features: np.ndarray
    edge_from: np.ndarray
    edge_to: np.ndarray
    edge_weights: np.ndarray
    base_slack: np.ndarray


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
    base = canonical_values(instance, cached)
    features = make_features(instance.node_wf_norm)
    edge_from = np.asarray(instance.edge_from, dtype=int)
    edge_to = np.asarray(instance.edge_to, dtype=int)
    edge_weights = np.rint(instance.edge_ext - (instance.k + 1) * instance.edge_d_min).astype(float)
    base_slack = base[edge_to] - base[edge_from] - edge_weights
    return MetricData(name, instance, base, features, edge_from, edge_to, edge_weights, base_slack)


def correction(features: np.ndarray, mode: str, branches: tuple[tuple[float, ...], ...]) -> np.ndarray:
    branch_array = np.asarray(branches, dtype=float)
    values = branch_array[:, 0][None, :] + features @ branch_array[:, 1:].T
    values = np.column_stack([np.zeros(len(features)), values])
    return np.max(values, axis=1) if mode == "max" else np.min(values, axis=1)


def correction_grid(features: np.ndarray, mode: str) -> np.ndarray:
    values = features @ BRANCH_GRID_ARRAY[:, 1:].T + BRANCH_GRID_ARRAY[:, 0][None, :]
    return np.maximum(values, 0.0) if mode == "max" else np.minimum(values, 0.0)


def potential_values(metric: MetricData, mode: str, branches: tuple[tuple[float, ...], ...]) -> np.ndarray:
    return metric.base + correction(metric.features, mode, branches)


def edge_weight(metric: MetricData) -> np.ndarray:
    return metric.edge_weights


def edge_slack(metric: MetricData, values: np.ndarray, indexes: np.ndarray | None = None) -> np.ndarray:
    slack = values[metric.edge_to] - values[metric.edge_from] - metric.edge_weights
    return slack if indexes is None else slack[indexes]


def active_arrays(active: dict[str, set[int]], metrics: dict[str, MetricData]):
    rows = []
    for name, indexes in active.items():
        metric = metrics[name]
        edge_indexes = np.asarray(sorted(indexes), dtype=int)
        rows.append((name, edge_indexes, metric.base_slack[edge_indexes], metric.features[metric.edge_from[edge_indexes]], metric.features[metric.edge_to[edge_indexes]]))
    return rows


def score_active_arrays(rows, mode: str, branches: tuple[tuple[float, ...], ...]) -> tuple[float, float]:
    minimum = float("inf")
    negative_sum = 0.0
    for _name, _edge_indexes, base_slack, from_features, to_features in rows:
        from_correction = correction(from_features, mode, branches)
        to_correction = correction(to_features, mode, branches)
        slack = base_slack + to_correction - from_correction
        minimum = min(minimum, float(np.min(slack)))
        negative_sum += float(np.sum(np.minimum(slack, 0.0)))
    return minimum, negative_sum


def score_active(active: dict[str, set[int]], metrics: dict[str, MetricData], mode: str, branches: tuple[tuple[float, ...], ...]) -> tuple[float, float]:
    """Reference-compatible wrapper that builds the active view once per call."""
    return score_active_arrays(active_arrays(active, metrics), mode, branches)


def score_single_grid(rows, mode: str) -> tuple[np.ndarray, np.ndarray]:
    minimum = np.full(len(BRANCH_GRID), float("inf"), dtype=float)
    negative_sum = np.zeros(len(BRANCH_GRID), dtype=float)
    for _name, _edge_indexes, base_slack, from_features, to_features in rows:
        from_correction = correction_grid(from_features, mode)
        to_correction = correction_grid(to_features, mode)
        slack = base_slack[:, None] + to_correction - from_correction
        minimum = np.minimum(minimum, np.min(slack, axis=0))
        negative_sum += np.sum(np.minimum(slack, 0.0), axis=0)
    return minimum, negative_sum


def best_single(rows, mode):
    minimum, negative_sum = score_single_grid(rows, mode)
    index = max(range(len(BRANCH_GRID)), key=lambda i: (minimum[i], negative_sum[i]))
    return BRANCH_GRID[index]


def top_singles(rows, mode, count):
    minimum, negative_sum = score_single_grid(rows, mode)
    indexes = sorted(range(len(BRANCH_GRID)), key=lambda i: (minimum[i], negative_sum[i]), reverse=True)
    return [BRANCH_GRID[i] for i in indexes[:count]]


def best_multi(rows, mode, branch_count, pool_count):
    pool = top_singles(rows, mode, pool_count)
    best = None
    for branches in itertools.combinations(pool, branch_count):
        score = score_active_arrays(rows, mode, branches)
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


def atomic_write_json(payload: dict[str, object]) -> None:
    temporary = OUTPUT.with_name(f".{OUTPUT.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, OUTPUT)


def checkpoint_payload(status: str, started: float, initial_active_counts: dict[str, int], active: dict[str, set[int]], trajectory: list[dict[str, object]], final_candidate) -> dict[str, object]:
    return {
        "status": status,
        "grammar": {
            "base": "published canonical n=5 potential",
            "features": FEATURE_NAMES,
            "feature_centers": {"wf_mean": 4.0, "wf_max": 7.0, "wf_std": 1.5},
            "coefficient_grid": list(FEATURE_GRID),
            "piece_hierarchy": ["max/min of 0 and one affine branch", "max/min of 0 and two affine branches", "max/min of 0 and three affine branches"],
        },
        "active_set_initialization": initial_active_counts,
        "active_set_current": {name: len(indexes) for name, indexes in active.items()},
        "trajectory": trajectory,
        "final_candidate": None if final_candidate is None else {key: value for key, value in final_candidate.items() if key != "values"},
        "elapsed_seconds": time.time() - started,
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
    initial_active_counts = {name: len(indexes) for name, indexes in active.items()}
    trajectory = []
    final_candidate = None
    for branch_count, pool_count in ((1, 0), (2, 32), (3, 24)):
        for mode in MODES:
            for iteration in range(4):
                if time.time() - started >= SCIENTIFIC_WALL_TIME:
                    result = checkpoint_payload("timeout", started, initial_active_counts, active, trajectory, final_candidate)
                    atomic_write_json(result)
                    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
                    print(OUTPUT, flush=True)
                    return 0
                active_view = active_arrays(active, metrics)
                if branch_count == 1:
                    branches = (best_single(active_view, mode),)
                else:
                    branches = best_multi(active_view, mode, branch_count, pool_count)
                values = {name: potential_values(metric, mode, branches) for name, metric in metrics.items()}
                audits = {name: audit(metric, values[name]) for name, metric in metrics.items()}
                taxi_violations = audits[taxi.name]["first_violated_edges"]
                circle_violations = audits[circle.name]["first_violated_edges"]
                taxi_added = sorted(set(taxi_violations) - active[taxi.name])
                circle_added = sorted(set(circle_violations) - active[circle.name])
                new_edges = set(taxi_violations) | set(circle_violations)
                trajectory.append({
                    "complexity": f"{branch_count + 1}-piece_{mode}",
                    "iteration": iteration,
                    "branches": [list(branch) for branch in branches],
                    "active_min_slack": score_active_arrays(active_view, mode, branches)[0],
                    "audits": audits,
                    "taxi_audit": audits[taxi.name],
                    "circle_audit": audits[circle.name],
                    "new_counterexamples": {
                        taxi.name: taxi_added,
                        circle.name: circle_added,
                    },
                    "elapsed_seconds": time.time() - started,
                })
                if not new_edges:
                    final_candidate = {"mode": mode, "branches": branches, "values": values, "audits": audits, "complexity": f"{branch_count + 1}-piece_{mode}"}
                    result = checkpoint_payload("running", started, initial_active_counts, active, trajectory, final_candidate)
                    atomic_write_json(result)
                    break
                active[taxi.name].update(taxi_violations)
                active[circle.name].update(circle_violations)
                result = checkpoint_payload("running", started, initial_active_counts, active, trajectory, final_candidate)
                atomic_write_json(result)
                if not taxi_added and not circle_added:
                    break
            if final_candidate is not None and final_candidate["audits"][taxi.name]["violations"] < 3 and final_candidate["audits"][circle.name]["violations"] == 0:
                break
        if final_candidate is not None and final_candidate["audits"][taxi.name]["violations"] < 3 and final_candidate["audits"][circle.name]["violations"] == 0:
            break
    result = checkpoint_payload("completed", started, initial_active_counts, active, trajectory, final_candidate)
    atomic_write_json(result)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    print(OUTPUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
