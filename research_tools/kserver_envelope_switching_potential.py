#!/usr/bin/env python3
"""Switch between the verified n=5 potential and published canonical alternatives."""

from __future__ import annotations

from kserver.potential.canonical_potential import Potential as CanonicalPotential


BASE_INDEX = [
    [-5, -5, -5, -5],
    [5, -1, -2, -2],
    [5, 1, 3, 4],
    [5, 2, -4, -4],
    [5, 2, 4, -3],
]
BASE_COEFS = [-1, 0, -1, 0, 1, 0, 0, -1, 0, 0]
UNIFYING_INDEX = [
    [1, 2, 3, 4],
    [-1, 2, 3, 4],
    [-2, -2, 3, 4],
    [-3, -3, -3, 4],
    [-4, -4, -4, -4],
]
KPLUS1_INDEX = [
    [1, 2, 3, 4],
    [1, 2, 3, 4],
    [-1, 2, 3, 4],
    [-2, -2, 3, 4],
    [-3, -3, -3, 4],
    [-4, -4, -4, -4],
]
SHINKA_COEFS = [1, -1, -1, -1, -1, -1, -1, 1, 1, 1]


def build_alternative(context, variant: str):
    if variant == "unifying":
        return CanonicalPotential(context, n=4, index_matrix=UNIFYING_INDEX, coefs=[0] * 6)
    if variant == "kplus1":
        return CanonicalPotential(context, n=4, index_matrix=KPLUS1_INDEX, coefs=[0] * 6)
    if variant == "shinka":
        return CanonicalPotential(context, n=5, index_matrix=UNIFYING_INDEX, coefs=SHINKA_COEFS)
    raise ValueError(f"unknown variant: {variant}")


class Potential:
    def __init__(self, context, variant="unifying", mode="max", offset=0):
        self.base = CanonicalPotential(context, n=5, index_matrix=BASE_INDEX, coefs=BASE_COEFS)
        self.alternative = build_alternative(context, variant)
        self.mode = str(mode)
        self.offset = float(offset)
        if self.mode not in {"max", "min"}:
            raise ValueError("mode must be max or min")

    def __call__(self, wf):
        base = self.base(wf)
        alt = self.alternative(wf)
        base_value = float(base[0] if isinstance(base, tuple) else base)
        alt_value = float(alt[0] if isinstance(alt, tuple) else alt) + self.offset
        return max(base_value, alt_value) if self.mode == "max" else min(base_value, alt_value)
