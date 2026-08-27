#!/usr/bin/env python3
"""Screen fixed max/min envelope switches against a pinned metric."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np

from kserver.evaluation import NumpyKServerInstance
from kserver_envelope_switching_potential import BASE_COEFS, BASE_INDEX, build_alternative
from kserver.potential.canonical_potential import Potential as CanonicalPotential

VARIANTS = ("unifying", "kplus1", "shinka")
MODES = ("max", "min")
OFFSETS = (-4, -2, 0, 2, 4)

_POTENTIALS = None
_WFS = None


def specs():
    return [
        {"candidate_id": f"{mode}_{variant}_{offset:+d}", "mode": mode, "variant": variant, "offset": offset}
        for variant in VARIANTS
        for mode in MODES
        for offset in OFFSETS
    ]


def _init_worker(context, wfs):
    global _POTENTIALS, _WFS
    _POTENTIALS = [
        CanonicalPotential(context, n=5, index_matrix=BASE_INDEX, coefs=BASE_COEFS),
        build_alternative(context, "unifying"),
        build_alternative(context, "kplus1"),
        build_alternative(context, "shinka"),
    ]
    _WFS = wfs


def _chunk(indexes):
    values = np.empty((len(indexes), 4), dtype=float)
    for row, index in enumerate(indexes):
        for col, potential in enumerate(_POTENTIALS):
            value = potential(_WFS[index])
            values[row, col] = float(value[0] if isinstance(value, tuple) else value)
    return indexes, values


def node_values(instance, workers):
    indexes = list(range(len(instance.node_id)))
    chunks = [indexes[start : start + 256] for start in range(0, len(indexes), 256)]
    values = np.empty((len(indexes), 4), dtype=float)
    with mp.get_context("fork").Pool(processes=workers, initializer=_init_worker, initargs=(instance.get_context(), instance.node_wf_norm)) as pool:
        for indexes_chunk, values_chunk in pool.imap(_chunk, chunks):
            values[indexes_chunk] = values_chunk
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metric", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--candidate-ids", nargs="*", default=None)
    args = parser.parse_args()
    started = time.time()
    instance = NumpyKServerInstance.load(args.metric)
    all_specs = specs()
    selected = all_specs if args.candidate_ids is None else [spec for spec in all_specs if spec["candidate_id"] in set(args.candidate_ids)]
    values = node_values(instance, args.workers)
    base = values[:, 0]
    alt_by_variant = {"unifying": values[:, 1], "kplus1": values[:, 2], "shinka": values[:, 3]}
    results = []
    for spec in selected:
        alt = alt_by_variant[spec["variant"]] + float(spec["offset"])
        combined = np.maximum(base, alt) if spec["mode"] == "max" else np.minimum(base, alt)
        slack = combined[instance.edge_to] - combined[instance.edge_from] + (instance.k + 1) * instance.edge_d_min - instance.edge_ext
        violated = np.flatnonzero(slack < 0)
        results.append({**spec, "violations_k": int(violated.size), "first_violated_edge_indexes": [int(index) for index in violated[:20]], "min_slack": float(np.min(slack))})
    result = {"status": "completed", "metric": args.metric.name, "nodes": int(len(instance.node_id)), "edges": int(len(instance.edge_from)), "candidate_count": len(selected), "workers": args.workers, "elapsed_s": time.time() - started, "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
