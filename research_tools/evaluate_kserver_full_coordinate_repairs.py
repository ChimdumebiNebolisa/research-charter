#!/usr/bin/env python3
"""Evaluate feasible full-coordinate repairs on every frozen taxi edge."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np

from kserver.evaluation import NumpyKServerInstance
from kserver.potential.canonical_potential import Potential as CanonicalPotential

from kserver_full_coordinate_linear_repair_potential import BASE_COEFS, INDEX_MATRIX, M6_CONFIGS

_POTENTIAL: CanonicalPotential | None = None
_WFS: np.ndarray | None = None


def _init_worker(context, wfs: np.ndarray) -> None:
    global _POTENTIAL, _WFS
    _POTENTIAL = CanonicalPotential(context, n=5, index_matrix=INDEX_MATRIX, coefs=BASE_COEFS)
    _WFS = wfs


def _potential_chunk(indexes: list[int]) -> tuple[list[int], np.ndarray]:
    assert _POTENTIAL is not None
    assert _WFS is not None
    return indexes, np.asarray([float(_POTENTIAL(_WFS[index])[0]) for index in indexes], dtype=float)


def base_values(instance: NumpyKServerInstance, workers: int) -> np.ndarray:
    indexes = list(range(len(instance.node_id)))
    chunks = [indexes[start : start + 1024] for start in range(0, len(indexes), 1024)]
    values = np.empty(len(indexes), dtype=float)
    with mp.get_context("fork").Pool(processes=workers, initializer=_init_worker, initargs=(instance.get_context(), instance.node_wf_norm)) as pool:
        for indexes_chunk, values_chunk in pool.imap(_potential_chunk, chunks):
            values[indexes_chunk] = values_chunk
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--taxi-metric", type=Path, required=True)
    parser.add_argument("--solve-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    started = time.time()
    taxi = NumpyKServerInstance.load(args.taxi_metric)
    solve = json.loads(args.solve_artifact.read_text(encoding="utf-8"))
    models = [model for model in solve["models"] if model.get("status") == "feasible"]
    base = base_values(taxi, args.workers)
    results = []
    for model_index, model in enumerate(models):
        correction = np.asarray(model["correction"], dtype=float)
        values = base + taxi.node_wf_norm @ correction
        slack = values[taxi.edge_to] - values[taxi.edge_from] + (taxi.k + 1) * taxi.edge_d_min - taxi.edge_ext
        violated = np.flatnonzero(slack < 0)
        results.append({"model_index": model_index, "target_residual_edges": model["target_residual_edges"], "violations_k": int(violated.size), "first_violated_edge_indexes": [int(index) for index in violated[:20]], "min_slack": float(np.min(slack)), "correction": model["correction"]})
    result = {"status": "completed", "metric": args.taxi_metric.name, "edges": int(len(taxi.edge_from)), "feasible_model_count": len(models), "results": results, "elapsed_s": time.time() - started}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
