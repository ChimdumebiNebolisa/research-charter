"""Candidate potential using a normalized entropic soft minimum."""

from __future__ import annotations

import math

import numpy as np

from kserver.potential.canonical_potential import Potential as CanonicalPotential


class Potential(CanonicalPotential):
    def __init__(self, context, **kwargs):
        self.temperature = float(kwargs.pop("temperature"))
        if not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError("temperature must be a positive finite number")
        super().__init__(context, **kwargs)

    def __call__(self, wf):
        energies = np.asarray(self._compute_candidate_values(wf), dtype=np.int64)
        minimum = int(energies.min())
        counts = np.bincount(energies - minimum)
        offsets = np.arange(counts.size, dtype=np.float64)
        weights = counts.astype(np.float64) * np.exp(-offsets / self.temperature)
        log_mean = math.log(float(weights.sum())) - math.log(float(energies.size))
        return float(minimum - self.temperature * log_mean)
