#!/usr/bin/env python3
"""Check how a finite taxi table transfers to the complete-circle metric."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from kserver.evaluation import NumpyKServerInstance


def row_key(row: np.ndarray) -> bytes:
    values = np.asarray(row, dtype=float)
    rounded = np.rint(values)
    if not np.allclose(values, rounded) or np.any(rounded < -64) or np.any(rounded > 64):
        return b"__out_of_domain__"
    return rounded.astype(np.int8).tobytes()


def check_metric(instance: NumpyKServerInstance, lookup: dict[bytes, int]) -> dict[str, object]:
    keys = [row_key(row) for row in instance.node_wf_norm]
    matched = np.asarray([key in lookup for key in keys], dtype=bool)
    values = np.asarray([lookup.get(key, 0) for key in keys], dtype=np.int64)
    weights = np.rint(instance.edge_ext - (instance.k + 1) * instance.edge_d_min).astype(np.int64)
    slack = values[instance.edge_to] - values[instance.edge_from] - weights
    violated = np.flatnonzero(slack < 0)
    return {
        "metric": "loaded",
        "nodes": int(len(instance.node_id)),
        "edges": int(len(instance.edge_from)),
        "matched_node_count": int(np.count_nonzero(matched)),
        "missing_node_count": int(np.count_nonzero(~matched)),
        "violations_with_zero_fallback": int(violated.size),
        "first_violated_edge_indexes": [int(index) for index in violated[:20]],
        "min_slack_with_zero_fallback": int(np.min(slack)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--taxi-metric", type=Path, required=True)
    parser.add_argument("--circle-metric", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    table = np.load(args.table)
    rows = np.asarray(table["node_wf_norm"])
    values = np.asarray(table["potential"], dtype=np.int64)
    lookup = {row_key(row): int(value) for row, value in zip(rows, values, strict=True)}
    taxi = NumpyKServerInstance.load(args.taxi_metric)
    circle = NumpyKServerInstance.load(args.circle_metric)
    taxi_result = check_metric(taxi, lookup)
    taxi_result["metric"] = args.taxi_metric.name
    circle_result = check_metric(circle, lookup)
    circle_result["metric"] = args.circle_metric.name
    result = {
        "status": "completed",
        "method": "cross_metric_finite_table_domain_audit",
        "table": str(args.table),
        "results": [taxi_result, circle_result],
        "interpretation": "zero fallback is only a diagnostic for out-of-domain rows, not a proposed generalization",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    print(args.output, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
