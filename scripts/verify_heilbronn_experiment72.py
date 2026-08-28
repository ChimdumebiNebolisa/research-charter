"""Independent Decimal verifier for the final Experiment 72 candidates."""

from __future__ import annotations

import itertools
import json
from decimal import Decimal, getcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "artifacts" / "heilbronn-experiment72.json"
BASELINE = ROOT / "artifacts" / "baselines" / "heilbronn_exact_verification.json"
STRUCTURAL = ROOT / "artifacts" / "heilbronn-experiment72-structural.json"
OUTPUT = ROOT / "artifacts" / "heilbronn-experiment72-independent-verification.json"


def determinant(points, triangle):
    i, j, k = triangle
    xi, yi = points[i]
    xj, yj = points[j]
    xk, yk = points[k]
    return (xj - xi) * (yk - yi) - (xk - xi) * (yj - yi)


def verify_candidate(vector, baseline, baseline_critical):
    points = [[Decimal(str(vector[2 * i])), Decimal(str(vector[2 * i + 1]))] for i in range(12)]
    triangles = list(itertools.combinations(range(12), 3))
    areas = [(tri, abs(determinant(points, tri)) / Decimal(2)) for tri in triangles]
    minimum = min(area for _, area in areas)
    active = [list(tri) for tri, area in areas if area <= minimum + Decimal("1e-12")]
    distinct = len({tuple(point) for point in points}) == 12
    in_square = all(Decimal(0) <= value <= Decimal(1) for point in points for value in point)
    return {
        "point_count": len(points),
        "triangle_count": len(triangles),
        "distinct_points": distinct,
        "all_points_in_unit_square": in_square,
        "zero_area_triangles": [list(tri) for tri, area in areas if area == 0],
        "minimum_area_decimal": str(minimum),
        "baseline_decimal": str(baseline),
        "gap_from_exact_baseline_decimal": str(minimum - baseline),
        "strictly_above_exact_baseline": minimum > baseline,
        "active_triangles_tolerance_1e-12": active,
        "active_set_matches_baseline_with_tolerance": set(map(tuple, active)) == set(map(tuple, baseline_critical)),
    }


def main():
    getcontext().prec = 110
    run = json.loads(RUN.read_text(encoding="utf-8"))
    baseline_doc = json.loads(BASELINE.read_text(encoding="utf-8"))
    structural = json.loads(STRUCTURAL.read_text(encoding="utf-8"))
    baseline = Decimal(baseline_doc["minimum_area_decimal"])
    baseline_critical = structural["minimum_triangles"]
    candidates = []
    for arm in run["arms"]:
        checked = verify_candidate(arm["final_coordinate_vector"], baseline, baseline_critical)
        checked.update({"arm": arm["arm"], "seed": arm["seed"]})
        candidates.append(checked)
    result = {
        "verification": "independent_decimal_all_220",
        "precision_digits": 110,
        "candidate_count": len(candidates),
        "baseline_source": str(BASELINE.relative_to(ROOT)),
        "structural_source": str(STRUCTURAL.relative_to(ROOT)),
        "candidates": candidates,
        "all_candidates_valid": all(
            item["distinct_points"] and item["all_points_in_unit_square"] and not item["zero_area_triangles"]
            for item in candidates
        ),
        "any_certified_improvement": any(item["strictly_above_exact_baseline"] for item in candidates),
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate_count": result["candidate_count"],
        "all_candidates_valid": result["all_candidates_valid"],
        "any_certified_improvement": result["any_certified_improvement"],
        "final_gaps": {f"{item['arm']}-{item['seed']}": item["gap_from_exact_baseline_decimal"] for item in candidates},
        "output": str(OUTPUT),
    }, indent=2))


if __name__ == "__main__":
    main()
