#!/usr/bin/env python3
"""High-precision verifier for a 12-point Heilbronn configuration."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, getcontext
from itertools import combinations
from pathlib import Path


def verify(points: list[list[str]], precision: int = 80) -> dict[str, object]:
    getcontext().prec = precision
    parsed = [(Decimal(str(x)), Decimal(str(y))) for x, y in points]
    errors: list[str] = []
    if len(parsed) != 12:
        errors.append(f"expected 12 points, got {len(parsed)}")
    if len(set(parsed)) != len(parsed):
        errors.append("points are not distinct")
    for index, (x, y) in enumerate(parsed):
        if not (Decimal(0) <= x <= Decimal(1) and Decimal(0) <= y <= Decimal(1)):
            errors.append(f"point {index} is outside the unit square")

    areas: list[tuple[Decimal, tuple[int, int, int]]] = []
    for i, j, k in combinations(range(len(parsed)), 3):
        xi, yi = parsed[i]
        xj, yj = parsed[j]
        xk, yk = parsed[k]
        determinant = (xj - xi) * (yk - yi) - (xk - xi) * (yj - yi)
        areas.append((abs(determinant) / Decimal(2), (i, j, k)))
    minimum = min(areas, default=(None, None))
    minima = [triple for area, triple in areas if area == minimum[0]]
    return {
        "valid": not errors and len(areas) == 220 and minimum[0] is not None and minimum[0] > 0,
        "errors": errors,
        "point_count": len(parsed),
        "triangle_count": len(areas),
        "precision_digits": precision,
        "minimum_area": str(minimum[0]) if minimum[0] is not None else None,
        "minimum_triangles": minima,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--precision", type=int, default=80)
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))
    result = verify(payload["points"], precision=args.precision)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
