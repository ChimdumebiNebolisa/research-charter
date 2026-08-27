#!/usr/bin/env python3
"""Independently audit finite relaxation tables against every taxi edge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from kserver.evaluation import NumpyKServerInstance


RESIDUAL_EDGE_INDEXES = (4766035, 5594108, 6193322)


def audit_table(instance: NumpyKServerInstance, table_path: Path) -> dict[str, object]:
    table = np.load(table_path)
    table_wfs = np.asarray(table["node_wf_norm"])
    potential = np.asarray(table["potential"], dtype=np.int64)
    if table_wfs.shape != instance.node_wf_norm.shape:
        raise ValueError(f"work-function shape mismatch for {table_path}")
    if not np.array_equal(table_wfs, np.asarray(instance.node_wf_norm)):
        raise ValueError(f"work-function rows mismatch for {table_path}")
    if potential.shape != (len(instance.node_id),):
        raise ValueError(f"potential shape mismatch for {table_path}")
    weights_float = np.asarray(instance.edge_ext - (instance.k + 1) * instance.edge_d_min, dtype=float)
    weights = np.rint(weights_float).astype(np.int64)
    if not np.allclose(weights_float, weights):
        raise ValueError("metric difference weights are not integral")
    slack = potential[instance.edge_to] - potential[instance.edge_from] - weights
    violated = np.flatnonzero(slack < 0)
    return {
        "table": str(table_path),
        "nodes": int(len(instance.node_id)),
        "edges": int(len(instance.edge_from)),
        "potential_min": int(np.min(potential)),
        "potential_max": int(np.max(potential)),
        "violations_k": int(violated.size),
        "first_violated_edge_indexes": [int(index) for index in violated[:20]],
        "min_slack": int(np.min(slack)),
        "residual_edge_slacks": {str(index): int(slack[index]) for index in RESIDUAL_EDGE_INDEXES},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--taxi-metric", type=Path, required=True)
    parser.add_argument("--table", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    instance = NumpyKServerInstance.load(args.taxi_metric)
    results = [audit_table(instance, path) for path in args.table]
    result = {
        "status": "completed",
        "method": "independent_integer_array_edge_audit",
        "constraint": "Phi(v)-Phi(u) >= ext-(k+1)*d_min",
        "metric": args.taxi_metric.name,
        "residual_edge_indexes": list(RESIDUAL_EDGE_INDEXES),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    print(args.output, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
