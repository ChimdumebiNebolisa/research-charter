#!/usr/bin/env python3
"""Generate the exact Comellas--Yebra baseline as decimal strings."""

from __future__ import annotations

import json
from pathlib import Path

import sympy as sp


def main() -> int:
    x = 1 - ((27 + 3 * sp.sqrt(57)) ** sp.Rational(2, 3) + 6) / (6 * (27 + 3 * sp.sqrt(57)) ** sp.Rational(1, 3))
    y = 2 * x**2 - 3 * x + sp.Rational(1, 2)
    points = [
        (x, 0), (1 - x, 0), (0, x), (1, x),
        (sp.Rational(1, 2), y), (y, sp.Rational(1, 2)),
        (1 - y, sp.Rational(1, 2)), (sp.Rational(1, 2), 1 - y),
        (0, 1 - x), (1, 1 - x), (x, 1), (1 - x, 1),
    ]
    payload = {
        "source": "Comellas-Yebra-2002",
        "parameters_exact": {"x": sp.sstr(x), "y": sp.sstr(y)},
        "baseline_area_exact": sp.sstr(x / 4 + x * y / 2 - x**2 / 2),
        "points": [[sp.N(px, 90).__str__(), sp.N(py, 90).__str__()] for px, py in points],
    }
    output = Path(__file__).resolve().parents[1] / "artifacts" / "baselines" / "heilbronn_comellas_yebra.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output)
    print(json.dumps({"x": str(sp.N(x, 50)), "y": str(sp.N(y, 50)), "baseline": str(sp.N(payload["baseline_area_exact"], 50))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
