#!/usr/bin/env python3
"""Solve finite taxi-graph difference constraints for the k-server diagnostic."""

from __future__ import annotations

import argparse
import gc
import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.optimize import linprog

from kserver.evaluation import NumpyKServerInstance


RESIDUAL_EDGE_INDEXES = (4766035, 5594108, 6193322)


def model_specs() -> list[tuple[str, tuple[int, ...]]]:
    specs = [("drop_none", ())]
    for pair in itertools.combinations(RESIDUAL_EDGE_INDEXES, 2):
        specs.append(("drop_pair_" + "_".join(str(index) for index in pair), pair))
    specs.append(("drop_all_three", RESIDUAL_EDGE_INDEXES))
    return specs


def solve_model(
    instance: NumpyKServerInstance,
    removed_edge_indexes: tuple[int, ...],
    model_time_limit: float,
) -> tuple[dict[str, object], np.ndarray | None]:
    started = time.time()
    node_count = len(instance.node_id)
    edge_count = len(instance.edge_from)
    removed = np.zeros(edge_count, dtype=bool)
    removed[list(removed_edge_indexes)] = True
    keep = ~removed
    kept_count = int(np.count_nonzero(keep))

    # Phi(v)-Phi(u) >= ext - (k+1)d_min is represented as
    # Phi(u)-Phi(v) <= -(ext - (k+1)d_min).
    rhs = instance.edge_ext - (instance.k + 1) * instance.edge_d_min
    from_nodes = np.asarray(instance.edge_from[keep], dtype=np.int32)
    to_nodes = np.asarray(instance.edge_to[keep], dtype=np.int32)
    b_ub = -np.asarray(rhs[keep], dtype=float)
    rows = np.arange(kept_count, dtype=np.int32)
    row_index = np.empty(2 * kept_count, dtype=np.int32)
    col_index = np.empty(2 * kept_count, dtype=np.int32)
    data = np.empty(2 * kept_count, dtype=float)
    row_index[:kept_count] = rows
    row_index[kept_count:] = rows
    col_index[:kept_count] = from_nodes
    col_index[kept_count:] = to_nodes
    data[:kept_count] = 1.0
    data[kept_count:] = -1.0
    matrix = coo_matrix(
        (data, (row_index, col_index)),
        shape=(kept_count, node_count),
    ).tocsr()
    del rows, row_index, col_index, data, from_nodes, to_nodes, b_ub
    gc.collect()

    # Potentials are translation-invariant; fix one node to zero.
    equality = csr_matrix(([1.0], ([0], [0])), shape=(1, node_count))
    result = linprog(
        np.zeros(node_count, dtype=float),
        A_ub=matrix,
        b_ub=-np.asarray(rhs[keep], dtype=float),
        A_eq=equality,
        b_eq=np.array([0.0]),
        bounds=(None, None),
        method="highs",
        options={"time_limit": model_time_limit},
    )
    del matrix, equality
    gc.collect()

    payload: dict[str, object] = {
        "removed_edge_indexes": list(removed_edge_indexes),
        "kept_edges": kept_count,
        "solver_status": int(result.status),
        "solver_message": result.message,
        "elapsed_s": time.time() - started,
    }
    if result.success:
        assert result.x is not None
        values = np.asarray(result.x, dtype=float)
        payload.update(
            {
                "status": "feasible",
                "potential_min": float(np.min(values)),
                "potential_max": float(np.max(values)),
                "potential_linf": float(np.max(np.abs(values))),
            }
        )
        return payload, values
    payload["status"] = "infeasible" if result.status == 2 else "solver_limit_or_failure"
    return payload, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--taxi-metric", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--potential-dir", type=Path, required=True)
    parser.add_argument("--model-time-limit", type=float, default=300.0)
    args = parser.parse_args()

    started = time.time()
    instance = NumpyKServerInstance.load(args.taxi_metric)
    edge_count = len(instance.edge_from)
    if edge_count <= max(RESIDUAL_EDGE_INDEXES):
        raise ValueError("taxi metric is missing a declared residual edge index")

    args.potential_dir.mkdir(parents=True, exist_ok=True)
    models: list[dict[str, object]] = []
    for label, removed in model_specs():
        print(f"starting {label} removed={list(removed)}", flush=True)
        payload, values = solve_model(instance, removed, args.model_time_limit)
        payload["model"] = label
        if values is not None:
            potential_path = args.potential_dir / f"kserver-finite-difference-feasibility-001-{label}.npz"
            np.savez_compressed(
                potential_path,
                node_wf_norm=np.asarray(instance.node_wf_norm),
                potential=values,
                removed_edge_indexes=np.asarray(removed, dtype=np.int64),
            )
            payload["potential_artifact"] = str(potential_path)
        models.append(payload)
        print(json.dumps(payload, sort_keys=True), flush=True)

    result = {
        "status": "completed",
        "method": "sparse_finite_difference_constraint_feasibility",
        "constraint": "Phi(v)-Phi(u) >= ext-(k+1)*d_min",
        "potential_contract": "one value per frozen taxi node; all taxi node work-functions are retained in feasible artifacts",
        "taxi_metric": args.taxi_metric.name,
        "nodes": int(len(instance.node_id)),
        "edges": int(edge_count),
        "residual_edge_indexes": list(RESIDUAL_EDGE_INDEXES),
        "models": models,
        "model_time_limit_s": args.model_time_limit,
        "elapsed_s": time.time() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    print(args.output, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
