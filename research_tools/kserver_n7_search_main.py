"""External workspace API adapter for the pinned k-server staged search.

The upstream search example expects a separately supplied ``main.py``. This
adapter exposes that API while delegating the potential and evaluator helpers
to the pinned k-servers package; it does not alter the upstream evaluator or
metric files.
"""

from __future__ import annotations

import multiprocessing as mp
import os
from typing import Any

import numpy as np

from kserver.evaluation import NumpyKServerInstance
from kserver.potential.canonical_potential import Potential


MATRIX = [
    [-1, -1, -1, -1],
    [1, -2, -3, -4],
    [1, 2, -5, -6],
    [1, 3, 5, -7],
    [1, 4, 6, 7],
]
N_COEFS = 21

_PARALLEL_POTENTIAL: Potential | None = None
_PARALLEL_NODES: Any = None


def default_canonical_kwargs() -> dict[str, Any]:
    return {"n": 7, "index_matrix": MATRIX, "coefs": [0] * N_COEFS}


def is_violation(u_potential: float, v_potential: float, d_min: float, ext: float, rho: float) -> bool:
    return v_potential - u_potential + (rho + 1) * d_min < ext


def _compute_one_node(node_idx: int) -> tuple[int, float]:
    assert _PARALLEL_POTENTIAL is not None
    value = _PARALLEL_POTENTIAL(_PARALLEL_NODES[int(node_idx)]["wf_norm"])
    if isinstance(value, tuple):
        value = value[0]
    return int(node_idx), float(value)


def compute_potentials_for_nodes(
    instance: NumpyKServerInstance,
    potential_kwargs: dict[str, Any],
    node_idxes: list[int] | None = None,
) -> dict[int, float]:
    context = instance.get_context()
    nodes = instance.get_nodes()
    indexes = list(range(len(nodes)) if node_idxes is None else node_idxes)
    if not indexes:
        return {}

    global _PARALLEL_POTENTIAL, _PARALLEL_NODES
    _PARALLEL_POTENTIAL = Potential(context, **potential_kwargs)
    _PARALLEL_NODES = nodes
    worker_count = min(12, os.cpu_count() or 1, len(indexes))
    if worker_count == 1:
        values = [_compute_one_node(node_idx) for node_idx in indexes]
    else:
        pool_context = mp.get_context("fork")
        with pool_context.Pool(processes=worker_count) as pool:
            values = pool.map(_compute_one_node, indexes, chunksize=max(1, len(indexes) // (worker_count * 8)))
    return dict(values)


def build_hard_edge_cache(
    instances: list[NumpyKServerInstance], potential_kwargs: dict[str, Any]
) -> list[dict[str, Any]]:
    del potential_kwargs
    # The upstream search only requires an ordered edge-index cache. Keeping
    # every pinned edge is conservative; the staged script applies its own
    # adaptive cap and adds observed violations afterward.
    return [{"edge_idxes": list(range(len(instance.get_edges())))} for instance in instances]
