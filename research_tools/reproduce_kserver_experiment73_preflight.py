"""Reproduce the k-server baseline and finite-table control metrics.

This preflight uses the pinned upstream potential/evaluator data but performs
the edge counts directly in one native process, avoiding benchmark changes and
making the control comparison auditable before Experiment 73 preregistration.
"""

from __future__ import annotations

import itertools
import json
import sys
import time
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
TABLE = ROOT / "artifacts" / "kserver-finite-difference-relaxation-001-drop_none.npz"
METRICS = UPSTREAM / "metrics"
OUTPUT = ROOT / "artifacts" / "kserver-experiment73-preflight.json"
RAW = ROOT / "experiments" / "kserver_k4_circle" / "raw" / "kserver-experiment73-preflight.json.txt"


def edge_audit(instance: NumpyKServerInstance, values: np.ndarray) -> dict[str, object]:
    weights = np.rint(instance.edge_ext - (instance.k + 1) * instance.edge_d_min).astype(np.int64)
    slack = values[instance.edge_to] - values[instance.edge_from] - weights
    violated = np.flatnonzero(slack < 0)
    return {
        "nodes": int(len(instance.node_id)),
        "edges": int(len(instance.edge_from)),
        "violations_k": int(violated.size),
        "first_violated_edge_indexes": [int(index) for index in violated[:20]],
        "min_slack": int(np.min(slack)),
        "potential_min": int(np.min(values)),
        "potential_max": int(np.max(values)),
    }


def canonical_values(instance: NumpyKServerInstance) -> np.ndarray:
    potential = CanonicalPotential(instance.get_context(), n=5, index_matrix=INDEX_MATRIX, coefs=COEFS)
    values = np.empty(len(instance.node_id), dtype=np.int64)
    for index, row in enumerate(instance.node_wf_norm):
        values[index] = int(potential(row)[0])
    return values


def row_key(row: np.ndarray) -> bytes:
    values = np.asarray(row, dtype=float)
    rounded = np.rint(values)
    if not np.allclose(values, rounded) or np.any(rounded < -64) or np.any(rounded > 64):
        return b"__out_of_domain__"
    return rounded.astype(np.int8).tobytes()


def table_values(instance: NumpyKServerInstance, require_rows_match: bool) -> tuple[np.ndarray, np.ndarray]:
    payload = np.load(TABLE)
    rows = np.asarray(payload["node_wf_norm"])
    values = np.asarray(payload["potential"], dtype=np.int64)
    if require_rows_match and not np.array_equal(rows, np.asarray(instance.node_wf_norm)):
        raise ValueError("finite-table rows do not match metric nodes")
    lookup = {row_key(row): int(value) for row, value in zip(rows, values, strict=True)}
    keys = np.asarray([row_key(row) for row in instance.node_wf_norm], dtype=object)
    matched = np.asarray([key in lookup for key in keys], dtype=bool)
    evaluated = np.asarray([lookup.get(key, 0) for key in keys], dtype=np.int64)
    return evaluated, matched


def main() -> int:
    started = time.time()
    names = ["circle_k4_m6.pickle", "circle_taxi_k4_m6.pickle"]
    result: dict[str, object] = {
        "status": "completed",
        "method": "independent_native_single_process_baseline_and_finite_table_reproduction",
        "upstream_commit": "aea64346b846c967e4448f098d4b8b1748504d27",
        "metrics": {},
    }
    for name in names:
        metric_started = time.time()
        instance = NumpyKServerInstance.load(METRICS / name)
        canonical = canonical_values(instance)
        canonical_audit = edge_audit(instance, canonical)
        table, matched = table_values(instance, require_rows_match=name == "circle_taxi_k4_m6.pickle")
        table_audit = edge_audit(instance, table)
        table_audit["matched_nodes"] = int(np.count_nonzero(matched))
        table_audit["missing_nodes"] = int(np.count_nonzero(~matched))
        result["metrics"][name] = {
            "canonical": canonical_audit,
            "finite_table": table_audit,
            "elapsed_seconds": time.time() - metric_started,
        }
    result["elapsed_seconds"] = time.time() - started
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    RAW.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    print(OUTPUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
