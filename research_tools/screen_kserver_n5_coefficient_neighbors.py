#!/usr/bin/env python3
"""Screen the published n=5 candidate and its declared one-step coefficient neighbors."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np

from kserver.evaluation import NumpyKServerInstance
from kserver.potential.canonical_potential import Potential


INDEX_MATRIX = [
    [-5, -5, -5, -5],
    [5, -1, -2, -2],
    [5, 1, 3, 4],
    [5, 2, -4, -4],
    [5, 2, 4, -3],
]
BASE_COEFS = [-1, 0, -1, 0, 1, 0, 0, -1, 0, 0]

_POTENTIALS: list[Potential] | None = None
_WFS: np.ndarray | None = None


def candidates() -> list[dict[str, object]]:
    result = [{"candidate_id": "control", "coefs": list(BASE_COEFS), "coordinate": None, "delta": 0}]
    for coordinate in range(len(BASE_COEFS)):
        for delta in (-1, 1):
            coefs = list(BASE_COEFS)
            coefs[coordinate] += delta
            result.append(
                {
                    "candidate_id": f"coef_{coordinate:02d}_{'minus' if delta < 0 else 'plus'}1",
                    "coefs": coefs,
                    "coordinate": coordinate,
                    "delta": delta,
                }
            )
    return result


def _init_worker(context, wfs: np.ndarray, specs: list[dict[str, object]]) -> None:
    global _POTENTIALS, _WFS
    _POTENTIALS = [
        Potential(context, n=5, index_matrix=INDEX_MATRIX, coefs=spec["coefs"])
        for spec in specs
    ]
    _WFS = wfs


def _potential_chunk(indexes: list[int]) -> tuple[list[int], np.ndarray]:
    assert _POTENTIALS is not None
    assert _WFS is not None
    values = np.empty((len(indexes), len(_POTENTIALS)), dtype=float)
    for row, index in enumerate(indexes):
        wf = _WFS[index]
        for column, potential in enumerate(_POTENTIALS):
            values[row, column] = float(potential(wf)[0])
    return indexes, values


def node_values(instance: NumpyKServerInstance, specs: list[dict[str, object]], workers: int) -> np.ndarray:
    indexes = list(range(len(instance.node_id)))
    chunks = [indexes[start : start + 256] for start in range(0, len(indexes), 256)]
    values = np.empty((len(indexes), len(specs)), dtype=float)
    with mp.get_context("fork").Pool(
        processes=workers,
        initializer=_init_worker,
        initargs=(instance.get_context(), instance.node_wf_norm, specs),
    ) as pool:
        for indexes_chunk, values_chunk in pool.imap(_potential_chunk, chunks):
            values[indexes_chunk] = values_chunk
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metric", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mp.set_start_method("fork")
    started = time.time()
    instance = NumpyKServerInstance.load(args.metric)
    specs = candidates()
    values = node_values(instance, specs, args.workers)
    slack = (
        values[instance.edge_to]
        - values[instance.edge_from]
        + (instance.k + 1) * instance.edge_d_min[:, None]
        - instance.edge_ext[:, None]
    )
    results = []
    for column, spec in enumerate(specs):
        violated = np.flatnonzero(slack[:, column] < 0)
        results.append(
            {
                **spec,
                "violations_k": int(violated.size),
                "first_violated_edge_indexes": [int(index) for index in violated[:20]],
                "min_slack": float(np.min(slack[:, column])),
            }
        )
    result = {
        "status": "completed",
        "metric": args.metric.name,
        "nodes": int(len(instance.node_id)),
        "edges": int(len(instance.edge_from)),
        "candidate_count": len(specs),
        "workers": args.workers,
        "elapsed_s": time.time() - started,
        "results": results,
        "target_gate_candidates": [
            spec["candidate_id"] for spec in results if spec["candidate_id"] != "control" and spec["violations_k"] == 0
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
