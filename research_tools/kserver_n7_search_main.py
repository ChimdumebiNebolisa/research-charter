"""External workspace API adapter for the pinned k-server staged search.

The upstream search example expects a separately supplied ``main.py``. This
adapter exposes that API while delegating the potential and evaluator helpers
to the pinned k-servers package; it does not alter the upstream evaluator or
metric files.
"""

from __future__ import annotations

from itertools import product
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


def default_canonical_kwargs() -> dict[str, Any]:
    return {"n": 7, "index_matrix": MATRIX, "coefs": [0] * N_COEFS}


def is_violation(u_potential: float, v_potential: float, d_min: float, ext: float, rho: float) -> bool:
    return v_potential - u_potential + (rho + 1) * d_min < ext


def compute_potentials_for_nodes(
    instance: NumpyKServerInstance,
    potential_kwargs: dict[str, Any],
    node_idxes: list[int] | None = None,
) -> dict[int, float]:
    context = instance.get_context()
    potential = Potential(context, **potential_kwargs)
    nodes = instance.get_nodes()
    indexes = range(len(nodes)) if node_idxes is None else node_idxes
    result: dict[int, float] = {}
    for node_idx in indexes:
        value = potential(nodes[int(node_idx)]["wf_norm"])
        if isinstance(value, tuple):
            value = value[0]
        result[int(node_idx)] = float(value)
    return result


def build_hard_edge_cache(
    instances: list[NumpyKServerInstance], potential_kwargs: dict[str, Any]
) -> list[dict[str, Any]]:
    del potential_kwargs
    # The upstream search only requires an ordered edge-index cache. Keeping
    # every pinned edge is conservative; the staged script applies its own
    # adaptive cap and adds observed violations afterward.
    return [{"edge_idxes": list(range(len(instance.get_edges())))} for instance in instances]
