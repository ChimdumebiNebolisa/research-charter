#!/usr/bin/env python3
"""Use direct longest-path relaxation for the finite k-server difference system."""

from __future__ import annotations

import argparse
import gc
import itertools
import json
import time
from pathlib import Path

import numpy as np
from numba import njit

from kserver.evaluation import NumpyKServerInstance


RESIDUAL_EDGE_INDEXES = (4766035, 5594108, 6193322)


def model_specs() -> list[tuple[str, tuple[int, ...]]]:
    specs = [("drop_none", ())]
    for pair in itertools.combinations(RESIDUAL_EDGE_INDEXES, 2):
        specs.append(("drop_pair_" + "_".join(str(index) for index in pair), pair))
    specs.append(("drop_all_three", RESIDUAL_EDGE_INDEXES))
    return specs


@njit(cache=True)
def relax_difference_system(
    edge_from: np.ndarray,
    edge_to: np.ndarray,
    weights: np.ndarray,
    node_count: int,
    skip0: int,
    skip1: int,
    skip2: int,
    max_passes: int,
    deadline: float,
) -> tuple[int, int, int, np.ndarray, np.ndarray]:
    """Return status, passes, witness node, values, and predecessor edges."""
    values = np.zeros(node_count, dtype=np.int64)
    predecessors = np.full(node_count, -1, dtype=np.int32)
    edge_count = edge_from.size
    for iteration in range(max_passes):
        if iteration % 8 == 0 and time.time() >= deadline:
            return 2, iteration, -1, values, predecessors
        next_values = values.copy()
        next_predecessors = predecessors.copy()
        changed = False
        changed_node = -1
        for edge_index in range(edge_count):
            if edge_index == skip0 or edge_index == skip1 or edge_index == skip2:
                continue
            source = edge_from[edge_index]
            target = edge_to[edge_index]
            candidate = values[source] + weights[edge_index]
            if candidate > next_values[target]:
                next_values[target] = candidate
                next_predecessors[target] = edge_index
                changed = True
                changed_node = target
        values = next_values
        predecessors = next_predecessors
        if not changed:
            return 0, iteration + 1, -1, values, predecessors
        if iteration + 1 >= node_count:
            return 1, iteration + 1, changed_node, values, predecessors
    return 3, max_passes, -1, values, predecessors


def cycle_from_predecessors(
    witness_node: int,
    predecessors: np.ndarray,
    edge_from: np.ndarray,
    edge_to: np.ndarray,
    weights: np.ndarray,
) -> dict[str, object]:
    node_count = len(predecessors)
    node = int(witness_node)
    for _ in range(node_count):
        edge_index = int(predecessors[node])
        if edge_index < 0:
            return {"status": "certificate_reconstruction_failed", "witness_node": node}
        node = int(edge_from[edge_index])
    start = node
    cycle_edges: list[int] = []
    cycle_nodes = [start]
    current = start
    for _ in range(node_count + 1):
        edge_index = int(predecessors[current])
        if edge_index < 0:
            return {"status": "certificate_reconstruction_failed", "witness_node": current}
        if int(edge_to[edge_index]) != current:
            return {"status": "certificate_reconstruction_failed", "witness_node": current}
        cycle_edges.append(edge_index)
        current = int(edge_from[edge_index])
        cycle_nodes.append(current)
        if current == start:
            total_weight = int(np.sum(weights[np.asarray(cycle_edges, dtype=np.int64)], dtype=np.int64))
            return {
                "status": "positive_cycle_certificate" if total_weight > 0 else "nonpositive_cycle_reconstruction",
                "edge_indexes": cycle_edges,
                "node_indexes": cycle_nodes,
                "length": len(cycle_edges),
                "weight_sum": total_weight,
            }
    return {"status": "certificate_reconstruction_failed", "witness_node": current}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--taxi-metric", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--potential-dir", type=Path, required=True)
    parser.add_argument("--wall-time-limit", type=float, default=1800.0)
    args = parser.parse_args()

    started = time.time()
    instance = NumpyKServerInstance.load(args.taxi_metric)
    edge_from = np.asarray(instance.edge_from, dtype=np.int32)
    edge_to = np.asarray(instance.edge_to, dtype=np.int32)
    weight_float = np.asarray(instance.edge_ext - (instance.k + 1) * instance.edge_d_min, dtype=float)
    weights = np.rint(weight_float).astype(np.int32)
    if not np.allclose(weight_float, weights):
        raise ValueError("difference weights are not integral")
    if len(edge_from) <= max(RESIDUAL_EDGE_INDEXES):
        raise ValueError("taxi metric is missing a declared residual edge index")

    args.potential_dir.mkdir(parents=True, exist_ok=True)
    max_passes = len(instance.node_id)
    models: list[dict[str, object]] = []
    for label, removed in model_specs():
        if time.time() - started >= args.wall_time_limit:
            models.append({"model": label, "removed_edge_indexes": list(removed), "status": "wall_time_limit_before_model"})
            continue
        skip = list(removed) + [-1] * (3 - len(removed))
        print(f"starting {label} removed={list(removed)}", flush=True)
        model_started = time.time()
        status, passes, witness_node, values, predecessors = relax_difference_system(
            edge_from,
            edge_to,
            weights,
            len(instance.node_id),
            skip[0],
            skip[1],
            skip[2],
            max_passes,
            started + args.wall_time_limit,
        )
        payload: dict[str, object] = {
            "model": label,
            "removed_edge_indexes": list(removed),
            "passes": int(passes),
            "elapsed_s": time.time() - model_started,
            "relaxation_status": int(status),
        }
        if status == 0:
            payload["status"] = "feasible_converged"
            payload["potential_min"] = int(np.min(values))
            payload["potential_max"] = int(np.max(values))
            potential_path = args.potential_dir / f"kserver-finite-difference-relaxation-001-{label}.npz"
            np.savez_compressed(
                potential_path,
                node_wf_norm=np.asarray(instance.node_wf_norm),
                potential=values,
                removed_edge_indexes=np.asarray(removed, dtype=np.int64),
            )
            payload["potential_artifact"] = str(potential_path)
        elif status == 1:
            certificate = cycle_from_predecessors(witness_node, predecessors, edge_from, edge_to, weights)
            payload["status"] = certificate.get("status", "positive_cycle_certificate")
            payload["witness_node"] = int(witness_node)
            payload["certificate"] = certificate
        elif status == 2:
            payload["status"] = "wall_time_limit"
        else:
            payload["status"] = "pass_limit"
        models.append(payload)
        print(json.dumps(payload, sort_keys=True), flush=True)
        del values, predecessors
        gc.collect()

    result = {
        "status": "completed",
        "method": "integer_longest_path_relaxation_for_difference_constraints",
        "constraint": "Phi(v)-Phi(u) >= ext-(k+1)*d_min",
        "certificate_rule": "a directed cycle with positive sum of integer difference weights is infeasible",
        "potential_contract": "one value per frozen taxi node; feasible tables are finite benchmark-specific artifacts",
        "taxi_metric": args.taxi_metric.name,
        "nodes": int(len(instance.node_id)),
        "edges": int(len(edge_from)),
        "residual_edge_indexes": list(RESIDUAL_EDGE_INDEXES),
        "models": models,
        "max_passes": max_passes,
        "wall_time_limit_s": args.wall_time_limit,
        "elapsed_s": time.time() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    print(args.output, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
