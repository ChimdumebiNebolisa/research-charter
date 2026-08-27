#!/usr/bin/env python3
"""Canonical n=5 potential plus a portable work-function feature correction."""

from __future__ import annotations

from itertools import combinations

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

# Pairwise circular-distance signatures present for k=4,m=6. The feature
# correction assigns one weight to the sum of wf_norm entries in each class.
FEATURE_SIGNATURES = [
    (0, 0, 0, 0, 0, 0),
    (0, 0, 0, 1, 1, 1),
    (0, 0, 0, 2, 2, 2),
    (0, 0, 0, 3, 3, 3),
    (0, 0, 1, 1, 1, 1),
    (0, 0, 2, 2, 2, 2),
    (0, 0, 3, 3, 3, 3),
    (0, 1, 1, 1, 1, 2),
    (0, 1, 1, 1, 2, 2),
    (0, 1, 1, 2, 2, 3),
    (0, 1, 1, 2, 3, 3),
    (0, 1, 2, 2, 3, 3),
    (0, 2, 2, 2, 2, 2),
    (1, 1, 1, 2, 2, 3),
    (1, 1, 2, 2, 2, 3),
    (1, 1, 2, 2, 3, 3),
]
SIGNATURE_INDEX = {signature: index for index, signature in enumerate(FEATURE_SIGNATURES)}


def _signature(config: tuple[int, ...], m: int) -> tuple[int, ...]:
    return tuple(sorted(min((a - b) % m, (b - a) % m) for a, b in combinations(config, 2)))


def feature_vector(context, wf: np.ndarray) -> np.ndarray:
    result = np.zeros(len(FEATURE_SIGNATURES), dtype=float)
    for index, config in enumerate(context._idx_to_config):
        feature_index = SIGNATURE_INDEX.get(_signature(config, context.m))
        if feature_index is not None:
            result[feature_index] += float(wf[index])
    return result


class Potential:
    def __init__(self, context, correction=None):
        self.base = CanonicalPotential(context, n=5, index_matrix=INDEX_MATRIX, coefs=BASE_COEFS)
        self.context = context
        self.correction = np.asarray(correction or [0.0] * len(FEATURE_SIGNATURES), dtype=float)
        if self.correction.shape != (len(FEATURE_SIGNATURES),):
            raise ValueError("correction must contain 16 feature weights")

    def __call__(self, wf):
        value = self.base(wf)
        base_value = value[0] if isinstance(value, tuple) else value
        return float(base_value) + float(np.dot(self.correction, feature_vector(self.context, wf)))
