#!/usr/bin/env python3
"""Solve the declared full-coordinate linear residual-repair diagnostic."""

from __future__ import annotations

import argparse
import json
import time
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from kserver.evaluation import NumpyKServerInstance
from kserver.potential.canonical_potential import Potential as CanonicalPotential

from kserver_full_coordinate_linear_repair_potential import BASE_COEFS, INDEX_MATRIX, M6_CONFIGS


RESIDUAL_EDGE_INDEXES = [4766035, 5594108, 6193322]


def base_values(instance: NumpyKServerInstance) -> np.ndarray:
    potential = CanonicalPotential(instance.get_context(), n=5, index_matrix=INDEX_MATRIX, coefs=BASE_COEFS)
    return np.asarray([float(potential(wf)[0]) for wf in instance.node_wf_norm], dtype=float)


def solve_model(circle, circle_base, taxi, taxi_base, target_indexes):
    feature_count = len(M6_CONFIGS)
    variable_count = feature_count * 2
    rows = []
    rhs = []

    def add_constraint(diff: np.ndarray, base_slack: float) -> None:
        row = np.zeros(variable_count, dtype=float)
        row[:feature_count] = -diff
        rows.append(row)
        rhs.append(float(base_slack))

    circle_slack = circle_base[circle.edge_to] - circle_base[circle.edge_from] + (circle.k + 1) * circle.edge_d_min - circle.edge_ext
    circle_features = circle.node_wf_norm
    for edge_index in range(len(circle.edge_from)):
        diff = circle_features[int(circle.edge_to[edge_index])] - circle_features[int(circle.edge_from[edge_index])]
        add_constraint(diff, circle_slack[edge_index])

    taxi_slack = taxi_base[taxi.edge_to] - taxi_base[taxi.edge_from] + (taxi.k + 1) * taxi.edge_d_min - taxi.edge_ext
    taxi_features = taxi.node_wf_norm
    for edge_index in target_indexes:
        diff = taxi_features[int(taxi.edge_to[edge_index])] - taxi_features[int(taxi.edge_from[edge_index])]
        add_constraint(diff, taxi_slack[edge_index])

    for index in range(feature_count):
        row = np.zeros(variable_count, dtype=float)
        row[index] = 1.0
        row[feature_count + index] = -1.0
        rows.append(row)
        rhs.append(0.0)
        row = np.zeros(variable_count, dtype=float)
        row[index] = -1.0
        row[feature_count + index] = -1.0
        rows.append(row)
        rhs.append(0.0)

    objective = np.r_[np.zeros(feature_count), np.ones(feature_count)]
    bounds = [(-10.0, 10.0)] * feature_count + [(0.0, 10.0)] * feature_count
    result = linprog(objective, A_ub=np.asarray(rows), b_ub=np.asarray(rhs), bounds=bounds, method="highs")
    if not result.success:
        return {"status": "infeasible_or_failed", "target_residual_edges": list(target_indexes), "message": result.message}
    correction = result.x[:feature_count]
    return {
        "status": "feasible",
        "target_residual_edges": list(target_indexes),
        "message": result.message,
        "correction": [float(value) for value in correction],
        "l1_norm": float(np.sum(np.abs(correction))),
        "max_abs": float(np.max(np.abs(correction))),
        "objective": float(result.fun),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--circle-metric", type=Path, required=True)
    parser.add_argument("--taxi-metric", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    circle = NumpyKServerInstance.load(args.circle_metric)
    taxi = NumpyKServerInstance.load(args.taxi_metric)
    circle_base = base_values(circle)
    taxi_base = base_values(taxi)
    targets = [RESIDUAL_EDGE_INDEXES, *[list(pair) for pair in combinations(RESIDUAL_EDGE_INDEXES, 2)]]
    models = [solve_model(circle, circle_base, taxi, taxi_base, target) for target in targets]
    result = {
        "status": "completed",
        "method": "bounded_l1_full_configuration_coordinate_slack_repair",
        "feature_definition": "all 126 normalized work-function coordinates for sorted 4-server multisets on m=6",
        "feature_count": len(M6_CONFIGS),
        "circle_metric": args.circle_metric.name,
        "taxi_metric": args.taxi_metric.name,
        "circle_edges": int(len(circle.edge_from)),
        "taxi_edges": int(len(taxi.edge_from)),
        "residual_edge_indexes": RESIDUAL_EDGE_INDEXES,
        "models": models,
        "elapsed_s": time.time() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
