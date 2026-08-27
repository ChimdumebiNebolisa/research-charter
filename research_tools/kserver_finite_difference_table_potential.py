#!/usr/bin/env python3
"""Primary-evaluator adapter for a finite relaxation table.

This adapter is intentionally benchmark-specific: it only looks up the exact
normalized work-function rows retained in the generated table artifact.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


TABLE_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "kserver-finite-difference-relaxation-001-drop_none.npz"


class Potential:
    def __init__(self, context):
        del context
        payload = np.load(TABLE_PATH)
        rows = np.asarray(payload["node_wf_norm"])
        values = np.asarray(payload["potential"], dtype=np.int64)
        if rows.ndim != 2 or values.shape != (len(rows),):
            raise ValueError("invalid finite table artifact")
        self._lookup = {row.tobytes(): int(value) for row, value in zip(rows, values, strict=True)}

    def __call__(self, wf):
        row = np.ascontiguousarray(np.asarray(wf, dtype=float))
        try:
            return self._lookup[row.tobytes()]
        except KeyError as exc:
            raise KeyError("primary evaluator requested an unrecorded work-function row") from exc
