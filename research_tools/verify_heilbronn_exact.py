#!/usr/bin/env python3
"""Independent high-precision symbolic-coordinate verification of the baseline."""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import sympy as sp


def main() -> int:
    x = 1 - ((27 + 3 * sp.sqrt(57)) ** sp.Rational(2, 3) + 6) / (6 * (27 + 3 * sp.sqrt(57)) ** sp.Rational(1, 3))
    y = 2 * x**2 - 3 * x + sp.Rational(1, 2)
    baseline = sp.expand(x / 4 + x * y / 2 - x**2 / 2)
    points = [
        (x, sp.Integer(0)), (1 - x, 0), (0, x), (1, x),
        (sp.Rational(1, 2), y), (y, sp.Rational(1, 2)),
        (1 - y, sp.Rational(1, 2)), (sp.Rational(1, 2), 1 - y),
        (0, 1 - x), (1, 1 - x), (x, 1), (1 - x, 1),
    ]
    areas: list[tuple[sp.Expr, tuple[int, int, int], float]] = []
    for i, j, k in combinations(range(12), 3):
        xi, yi = points[i]
        xj, yj = points[j]
        xk, yk = points[k]
        determinant = (xj - xi) * (yk - yi) - (xk - xi) * (yj - yi)
        numeric_area = abs(float(sp.N(determinant, 100))) / 2.0
        exact_area = determinant / 2 if numeric_area >= 0 and float(sp.N(determinant, 30)) >= 0 else -determinant / 2
        areas.append((sp.expand(exact_area), (i, j, k), numeric_area))

    ordered = sorted(areas, key=lambda item: item[2])
    minimum = ordered[0][0]
    minimum_numeric = ordered[0][2]
    minima = [triple for area, triple, numeric_area in areas if abs(numeric_area - minimum_numeric) < 1e-70]
    exact_gap = minimum - baseline
    result = {
        "point_count": len(points),
        "triangle_count": len(areas),
        "minimum_area_exact": sp.sstr(minimum),
        "minimum_area_decimal": sp.N(minimum, 80).__str__(),
        "minimum_area_numeric_ordering": format(minimum_numeric, ".17g"),
        "minimum_triangles": minima,
        "baseline_exact": sp.sstr(baseline),
        "minimum_minus_baseline_exact": sp.sstr(exact_gap),
        "minimum_equals_frozen_baseline": abs(float(sp.N(exact_gap, 100))) < 1e-70,
        "all_points_in_unit_square": all(0 <= float(sp.N(value, 50)) <= 1 for point in points for value in point),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    output = Path(__file__).resolve().parents[1] / "artifacts" / "baselines" / "heilbronn_exact_verification.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result["minimum_equals_frozen_baseline"] and result["all_points_in_unit_square"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
