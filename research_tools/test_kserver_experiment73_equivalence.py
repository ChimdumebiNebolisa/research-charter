"""Deterministic reference-vs-optimized semantics gate for Experiment 73."""

from __future__ import annotations

import importlib.util
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "research_tools" / "synthesize_kserver_experiment73.py"
OUTPUT = ROOT / "artifacts" / "kserver-experiment73-equivalence.json"


def load_synthesizer():
    spec = importlib.util.spec_from_file_location("e73_optimized", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def reference_correction(features: np.ndarray, mode: str, branches):
    values = np.column_stack([
        branch[0] + features @ np.asarray(branch[1:], dtype=float)
        for branch in branches
    ])
    values = np.column_stack([np.zeros(len(features)), values])
    return np.max(values, axis=1) if mode == "max" else np.min(values, axis=1)


def reference_score(rows, mode: str, branches):
    minimum = float("inf")
    negative_sum = 0.0
    for _name, _indexes, base_slack, from_features, to_features in rows:
        slack = base_slack + reference_correction(to_features, mode, branches) - reference_correction(from_features, mode, branches)
        minimum = min(minimum, float(np.min(slack)))
        negative_sum += float(np.sum(np.minimum(slack, 0.0)))
    return minimum, negative_sum


def reference_rows(active, metrics):
    rows = []
    for name, indexes in active.items():
        metric = metrics[name]
        edge_indexes = np.asarray(sorted(indexes), dtype=int)
        instance = metric.instance
        weights = np.rint(instance.edge_ext[edge_indexes] - (instance.k + 1) * instance.edge_d_min[edge_indexes]).astype(float)
        base_slack = metric.base[instance.edge_to[edge_indexes]] - metric.base[instance.edge_from[edge_indexes]] - weights
        rows.append((name, edge_indexes, base_slack, metric.features[instance.edge_from[edge_indexes]], metric.features[instance.edge_to[edge_indexes]]))
    return rows


def assert_close(left, right, label):
    if not np.allclose(left, right, rtol=0.0, atol=1e-12):
        raise AssertionError(f"{label}: {left!r} != {right!r}")


def main() -> int:
    started = time.perf_counter()
    m = load_synthesizer()
    cache = np.load(m.TAXI_CACHE)
    taxi = m.load_metric("circle_taxi_k4_m6.pickle", cache["canonical"])
    circle = m.load_metric("circle_k4_m6.pickle")
    metrics = {taxi.name: taxi, circle.name: circle}
    taxi_edges = np.asarray([4766035, 5594108, 6193322, 0, 1, 2, 1000, 50000], dtype=int)
    circle_edges = np.asarray([0, 1, 2, 293, 365, 6005], dtype=int)
    active = {taxi.name: set(taxi_edges.tolist()), circle.name: set(circle_edges.tolist())}
    optimized_rows = m.active_arrays(active, metrics)
    reference = reference_rows(active, metrics)
    for optimized_row, reference_row in zip(optimized_rows, reference):
        assert optimized_row[0] == reference_row[0]
        assert np.array_equal(optimized_row[1], reference_row[1])
        assert_close(optimized_row[2], reference_row[2], "base slack")
        assert_close(optimized_row[3], reference_row[3], "source features")
        assert_close(optimized_row[4], reference_row[4], "destination features")

    branch_cases = [
        ("max", (m.BRANCH_GRID[0],)),
        ("min", (m.BRANCH_GRID[-1],)),
        ("max", (m.BRANCH_GRID[10], m.BRANCH_GRID[100])),
        ("min", (m.BRANCH_GRID[20], m.BRANCH_GRID[200], m.BRANCH_GRID[400])),
    ]
    for mode, branches in branch_cases:
        for optimized_row, reference_row in zip(optimized_rows, reference):
            optimized_correction_from = m.correction(optimized_row[3], mode, branches)
            reference_correction_from = reference_correction(reference_row[3], mode, branches)
            optimized_correction_to = m.correction(optimized_row[4], mode, branches)
            reference_correction_to = reference_correction(reference_row[4], mode, branches)
            assert_close(optimized_correction_from, reference_correction_from, f"{mode} source correction")
            assert_close(optimized_correction_to, reference_correction_to, f"{mode} destination correction")
        assert_close(m.score_active_arrays(optimized_rows, mode, branches), reference_score(reference, mode, branches), f"{mode} score")

    for mode in m.MODES:
        optimized_best = m.best_single(optimized_rows, mode)
        reference_scores = [(reference_score(reference, mode, (branch,)), branch) for branch in m.BRANCH_GRID]
        reference_best = max(reference_scores, key=lambda item: (item[0][0], item[0][1]))[1]
        if optimized_best != reference_best:
            raise AssertionError(f"{mode} best-single ranking mismatch: {optimized_best!r} != {reference_best!r}")
        optimized_multi = m.best_multi(optimized_rows, mode, 2, 5)
        reference_pool = sorted(reference_scores, reverse=True, key=lambda item: (item[0][0], item[0][1]))[:5]
        reference_multi_scores = [(reference_score(reference, mode, branches), branches) for branches in itertools.combinations([branch for _score, branch in reference_pool], 2)]
        reference_multi = max(reference_multi_scores, key=lambda item: (item[0][0], item[0][1]))[1]
        if optimized_multi != reference_multi:
            raise AssertionError(f"{mode} multi-branch ranking mismatch: {optimized_multi!r} != {reference_multi!r}")

    result = {
        "status": "passed",
        "metrics": {name: {"active_edges": len(indexes), "total_edges": len(metrics[name].edge_weights)} for name, indexes in active.items()},
        "branch_cases": len(branch_cases),
        "modes": list(m.MODES),
        "checks": ["correction_values", "active_edge_slacks", "minimum_slack", "negative_slack_sum", "single_branch_ranking", "multi_branch_ranking"],
        "tolerance": 1e-12,
        "elapsed_seconds": time.perf_counter() - started,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
