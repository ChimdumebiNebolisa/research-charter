#!/usr/bin/env python3
"""Independently count the frozen k-server violations for the known n=5 candidate."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np

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

_POTENTIAL: CanonicalPotential | None = None
_WFS: np.ndarray | None = None


def _init_worker(context, wfs: np.ndarray) -> None:
    global _POTENTIAL, _WFS
    _POTENTIAL = CanonicalPotential(context, n=5, index_matrix=INDEX_MATRIX, coefs=COEFS)
    _WFS = wfs


def _potential_chunk(indexes: list[int]) -> list[tuple[int, float]]:
    assert _POTENTIAL is not None
    assert _WFS is not None
    return [(index, float(_POTENTIAL(_WFS[index])[0])) for index in indexes]


def _node_potentials(instance: NumpyKServerInstance, workers: int) -> np.ndarray:
    indexes = list(range(len(instance.node_id)))
    chunks = [indexes[start : start + 1024] for start in range(0, len(indexes), 1024)]
    values = np.empty(len(indexes), dtype=float)
    if workers == 1:
        _init_worker(instance.get_context(), instance.node_wf_norm)
        results = [_potential_chunk(chunk) for chunk in chunks]
    else:
        with mp.get_context("fork").Pool(
            processes=workers,
            initializer=_init_worker,
            initargs=(instance.get_context(), instance.node_wf_norm),
        ) as pool:
            results = pool.map(_potential_chunk, chunks)
    for chunk in results:
        for index, value in chunk:
            values[index] = value
    return values


def count_metric(path: Path, workers: int) -> dict[str, object]:
    started = time.time()
    instance = NumpyKServerInstance.load(path)
    potentials = _node_potentials(instance, workers)
    slack = (
        potentials[instance.edge_to]
        - potentials[instance.edge_from]
        + (instance.k + 1) * instance.edge_d_min
        - instance.edge_ext
    )
    violated = np.flatnonzero(slack < 0)
    return {
        "metric": path.name,
        "nodes": int(len(instance.node_id)),
        "edges": int(len(instance.edge_from)),
        "violations_k": int(violated.size),
        "first_violated_edge_indexes": [int(index) for index in violated[:20]],
        "min_slack": float(np.min(slack)),
        "elapsed_s": time.time() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics-path", type=Path, required=True)
    parser.add_argument("--metrics-names", nargs="+", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mp.set_start_method("fork")
    result = {
        "candidate": "kserver-known3-reproduction-001",
        "method": "direct-canonical-potential-and-array-inequality-count",
        "workers": args.workers,
        "metrics": [count_metric(args.metrics_path / name, args.workers) for name in args.metrics_names],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
