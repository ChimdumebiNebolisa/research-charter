#!/usr/bin/env python3
"""Canonical n=5 potential plus a full m=6 configuration-coordinate correction."""

from __future__ import annotations

from itertools import combinations_with_replacement

import numpy as np

from kserver.potential.canonical_potential import Potential as CanonicalPotential


INDEX_MATRIX = [
    [-5, -5, -5, -5],
    [5, -1, -2, -2],
    [5, 1, 3, 4],
    [5, 2, -4, -4],
    [5, 2, 4, -3],
]
BASE_COEFS = [-1, 0, -1, 0, 1, 0, 0, -1, 0, 0]
M6_CONFIGS = list(combinations_with_replacement(range(6), 4))


def feature_vector(context, wf: np.ndarray) -> np.ndarray:
    """Map the fixed m=6 configuration coordinates into the active context."""
    result = np.zeros(len(M6_CONFIGS), dtype=float)
    for index, config in enumerate(M6_CONFIGS):
        target_index = context._config_to_idx.get(config)
        if target_index is not None:
            result[index] = float(wf[target_index])
    return result


class Potential:
    def __init__(self, context, correction=None):
        self.base = CanonicalPotential(context, n=5, index_matrix=INDEX_MATRIX, coefs=BASE_COEFS)
        self.context = context
        self.correction = np.asarray(correction or [0.0] * len(M6_CONFIGS), dtype=float)
        if self.correction.shape != (len(M6_CONFIGS),):
            raise ValueError("correction must contain 126 configuration weights")

    def __call__(self, wf):
        value = self.base(wf)
        base_value = value[0] if isinstance(value, tuple) else value
        return float(base_value) + float(np.dot(self.correction, feature_vector(self.context, wf)))
