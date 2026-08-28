"""Structural audit and bounded orbit-relaxed homotopy for Heilbronn n=12.

The structural mode is intentionally usable before any nonlinear search.  It
reconstructs the source-faithful Comellas--Yebra configuration, enumerates all
220 triangles, computes the D4 orbits of the exact minimum set, and tests the
first-order ascent cones with the unit-square boundary tangent cone.
"""

from __future__ import annotations

import argparse
import itertools
import json
from decimal import Decimal, getcontext
from pathlib import Path

import numpy as np
import sympy as sp
from scipy.optimize import linprog


ROOT = Path(__file__).resolve().parents[1]
BASELINE_ARTIFACT = ROOT / "artifacts" / "baselines" / "heilbronn_comellas_yebra.json"
STRUCTURAL_ARTIFACT = ROOT / "artifacts" / "heilbronn-experiment72-structural.json"
RUN_ARTIFACT = ROOT / "artifacts" / "heilbronn-experiment72.json"
RUN_RAW = ROOT / "experiments" / "heilbronn_n12" / "raw" / "heilbronn-experiment72.json.txt"
SCHEDULE = [0.00, 0.10, 0.25, 0.50, 0.75, 0.90, 0.97, 1.00]


def baseline_symbolic_points() -> list[tuple[sp.Expr, sp.Expr]]:
    a = sp.Integer(27) + 3 * sp.sqrt(57)
    x = 1 - (a ** sp.Rational(2, 3) + 6) / (6 * a ** sp.Rational(1, 3))
    y = 2 * x**2 - 3 * x + sp.Rational(1, 2)
    return [
        (x, 0),
        (1 - x, 0),
        (0, x),
        (1, x),
        (sp.Rational(1, 2), y),
        (y, sp.Rational(1, 2)),
        (1 - y, sp.Rational(1, 2)),
        (sp.Rational(1, 2), 1 - y),
        (0, 1 - x),
        (1, 1 - x),
        (x, 1),
        (1 - x, 1),
    ]


def det(p_i, p_j, p_k):
    xi, yi = p_i
    xj, yj = p_j
    xk, yk = p_k
    return (xj - xi) * (yk - yi) - (xk - xi) * (yj - yi)


def d4_transforms(point):
    x, y = point
    return {
        "identity": (x, y),
        "rot90": (1 - y, x),
        "rot180": (1 - x, 1 - y),
        "rot270": (y, 1 - x),
        "reflect_x": (1 - x, y),
        "reflect_y": (x, 1 - y),
        "reflect_diag": (y, x),
        "reflect_anti": (1 - y, 1 - x),
    }


def numerical_point_index(points, target, digits=100):
    tx, ty = (float(sp.N(v, digits)) for v in target)
    distances = [
        (float(sp.N(px, digits)) - tx) ** 2 + (float(sp.N(py, digits)) - ty) ** 2
        for px, py in points
    ]
    index = int(np.argmin(distances))
    if distances[index] > 1e-24:
        raise RuntimeError(f"D4 image did not match a baseline point: {target}")
    return index


def d4_permutations(points):
    permutations = {}
    for name in d4_transforms((sp.Symbol("u"), sp.Symbol("v"))).keys():
        perm = tuple(numerical_point_index(points, d4_transforms(points[i])[name]) for i in range(12))
        permutations[name] = perm
    return permutations


def signed_area_gradient(points, triangle):
    i, j, k = triangle
    p_i, p_j, p_k = points[i], points[j], points[k]
    value = det(p_i, p_j, p_k)
    sign = 1 if float(sp.N(value, 80)) > 0 else -1
    xi, yi = (float(sp.N(v, 80)) for v in p_i)
    xj, yj = (float(sp.N(v, 80)) for v in p_j)
    xk, yk = (float(sp.N(v, 80)) for v in p_k)
    g = np.zeros(24, dtype=float)
    # Gradient of the signed doubled area, with the baseline orientation made
    # positive by multiplying by sign(det).  The factor 1/2 is immaterial for
    # cone feasibility and is omitted consistently.
    g[2 * i : 2 * i + 2] = sign * np.array([yj - yk, xk - xj])
    g[2 * j : 2 * j + 2] = sign * np.array([yk - yi, xi - xk])
    g[2 * k : 2 * k + 2] = sign * np.array([yi - yj, xj - xi])
    return g


def boundary_inequalities(points):
    rows = []
    labels = []
    eps = 1e-12
    for i, (x, y) in enumerate(points):
        xf = float(sp.N(x, 80))
        yf = float(sp.N(y, 80))
        if abs(xf) < eps:
            row = np.zeros(24)
            row[2 * i] = -1.0  # dx_i >= 0
            rows.append(row)
            labels.append(f"dx[{i}]>=0")
        elif abs(xf - 1) < eps:
            row = np.zeros(24)
            row[2 * i] = 1.0  # dx_i <= 0
            rows.append(row)
            labels.append(f"dx[{i}]<=0")
        if abs(yf) < eps:
            row = np.zeros(24)
            row[2 * i + 1] = -1.0  # dy_i >= 0
            rows.append(row)
            labels.append(f"dy[{i}]>=0")
        elif abs(yf - 1) < eps:
            row = np.zeros(24)
            row[2 * i + 1] = 1.0  # dy_i <= 0
            rows.append(row)
            labels.append(f"dy[{i}]<=0")
    return rows, labels


def nonzero_cone_feasible(gradients, boundary_rows):
    a_ub = [-g for g in gradients] + list(boundary_rows)
    a_ub = np.asarray(a_ub, dtype=float)
    b_ub = np.zeros(len(a_ub), dtype=float)
    for coordinate in range(24):
        for sign in (-1.0, 1.0):
            a_eq = np.zeros((1, 24), dtype=float)
            a_eq[0, coordinate] = 1.0
            result = linprog(
                np.zeros(24),
                A_ub=a_ub,
                b_ub=b_ub,
                A_eq=a_eq,
                b_eq=np.array([sign]),
                bounds=[(None, None)] * 24,
                method="highs",
            )
            if result.success:
                return {
                    "feasible": True,
                    "coordinate_fixed": coordinate,
                    "coordinate_value": sign,
                    "direction": [float(v) for v in result.x],
                }
    return {"feasible": False}


def ascent_margin(gradients, boundary_rows):
    # Maximize t subject to every retained active area derivative >= t and
    # ||d||_infinity <= 1.  This is a bounded, scale-normalized common ascent
    # margin in doubled-area units.
    a_ub = []
    b_ub = []
    for g in gradients:
        row = np.zeros(25)
        row[:24] = -g
        row[24] = 1.0
        a_ub.append(row)
        b_ub.append(0.0)
    for row24 in boundary_rows:
        row = np.zeros(25)
        row[:24] = row24
        a_ub.append(row)
        b_ub.append(0.0)
    bounds = [(-1.0, 1.0)] * 24 + [(None, None)]
    result = linprog(
        np.r_[np.zeros(24), -1.0],
        A_ub=np.asarray(a_ub),
        b_ub=np.asarray(b_ub),
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"ascent-margin LP failed: {result.message}")
    return {
        "common_doubled_area_derivative": float(result.x[24]),
        "direction": [float(v) for v in result.x[:24]],
    }


def structural_audit():
    points = baseline_symbolic_points()
    a = sp.Integer(27) + 3 * sp.sqrt(57)
    x = 1 - (a ** sp.Rational(2, 3) + 6) / (6 * a ** sp.Rational(1, 3))
    y = 2 * x**2 - 3 * x + sp.Rational(1, 2)
    baseline_area = x / 4 + x * y / 2 - x**2 / 2
    getcontext().prec = 120
    baseline_decimal = Decimal(str(sp.N(baseline_area, 115)))
    triangles = list(itertools.combinations(range(12), 3))
    signed = {tri: det(points[tri[0]], points[tri[1]], points[tri[2]]) for tri in triangles}
    areas = {}
    area_decimals = {}
    for tri, value in signed.items():
        sign = 1 if float(sp.N(value, 50)) > 0 else -1
        area = sign * value / 2
        areas[tri] = area
        area_decimals[tri] = Decimal(str(sp.N(area, 115)))
    min_area_decimal = min(area_decimals.values())
    critical = [tri for tri in triangles if abs(area_decimals[tri] - baseline_decimal) < Decimal("1e-105")]
    if len(critical) != 20:
        raise RuntimeError(f"expected 20 critical triangles, found {len(critical)}")

    permutations = d4_permutations(points)
    critical_set = set(critical)
    orbit_sets = []
    unseen = set(critical)
    while unseen:
        seed = min(unseen)
        orbit = set()
        for perm in permutations.values():
            mapped = tuple(sorted(perm[i] for i in seed))
            if mapped in critical_set:
                orbit.add(mapped)
        orbit_sets.append(sorted(orbit))
        unseen -= orbit
    orbit_sets.sort(key=lambda orbit: (len(orbit), orbit))
    labels = {}
    for index, orbit in enumerate(orbit_sets):
        label = chr(ord("A") + index)
        for tri in orbit:
            labels[tri] = label

    boundary_rows, boundary_labels = boundary_inequalities(points)
    full_gradients = [signed_area_gradient(points, tri) for tri in critical]
    cone_full = nonzero_cone_feasible(full_gradients, boundary_rows)
    margin_full = ascent_margin(full_gradients, boundary_rows)
    relaxed = {}
    for index, orbit in enumerate(orbit_sets):
        retained = [tri for tri in critical if tri not in set(orbit)]
        gradients = [signed_area_gradient(points, tri) for tri in retained]
        relaxed[chr(ord("A") + index)] = {
            "excluded_orbit": orbit,
            "retained_critical_count": len(retained),
            "nonzero_cone": nonzero_cone_feasible(gradients, boundary_rows),
            "ascent_margin": ascent_margin(gradients, boundary_rows),
        }

    result = {
        "experiment": "72",
        "problem_id": "heilbronn_n12",
        "target_id": "heilbronn_n12_min_area_gt_comellas_yebra",
        "baseline_area_exact": str(baseline_area),
        "baseline_area_decimal_100": str(sp.N(baseline_area, 100)),
        "minimum_area_decimal_115": str(min_area_decimal),
        "point_count": len(points),
        "triangle_count": len(triangles),
        "minimum_triangle_count": len(critical),
        "minimum_triangles": [list(tri) for tri in critical],
        "d4_point_permutations": {name: list(perm) for name, perm in permutations.items()},
        "critical_orbits": {chr(ord("A") + i): [list(tri) for tri in orbit] for i, orbit in enumerate(orbit_sets)},
        "boundary_tangent_constraints": boundary_labels,
        "full_active_set": {
            "nonzero_feasible_direction": cone_full,
            "ascent_margin": margin_full,
        },
        "relaxed_orbits": relaxed,
    }
    return result


def float_baseline_data():
    symbolic_points = baseline_symbolic_points()
    points = np.asarray([[float(sp.N(x, 80)), float(sp.N(y, 80))] for x, y in symbolic_points])
    triangles = list(itertools.combinations(range(12), 3))
    signs = []
    for tri in triangles:
        signs.append(1.0 if float(sp.N(det(*[symbolic_points[i] for i in tri]), 60)) > 0 else -1.0)
    a = sp.Integer(27) + 3 * sp.sqrt(57)
    x = 1 - (a ** sp.Rational(2, 3) + 6) / (6 * a ** sp.Rational(1, 3))
    y = 2 * x**2 - 3 * x + sp.Rational(1, 2)
    baseline = float(sp.N(x / 4 + x * y / 2 - x**2 / 2, 80))
    return points, np.asarray(triangles, dtype=int), np.asarray(signs), baseline


def determinants(coords, triangles):
    p_i = coords[triangles[:, 0]]
    p_j = coords[triangles[:, 1]]
    p_k = coords[triangles[:, 2]]
    return (
        (p_j[:, 0] - p_i[:, 0]) * (p_k[:, 1] - p_i[:, 1])
        - (p_k[:, 0] - p_i[:, 0]) * (p_j[:, 1] - p_i[:, 1])
    )


def true_area_data(coords, triangles):
    values = np.abs(determinants(coords, triangles)) / 2.0
    minimum = float(np.min(values))
    active = [list(map(int, tri)) for tri, value in zip(triangles, values) if value <= minimum + 1e-8]
    return minimum, active, values


def homotopy_constraints(vector, triangles, signs, selected, lam):
    coords = vector[:24].reshape(12, 2)
    t = vector[24]
    signed_areas = signs * determinants(coords, triangles) / 2.0
    weights = np.ones(len(triangles))
    if selected:
        weights[np.asarray([tuple(tri) in selected for tri in triangles])] = lam
    return signed_areas - weights * t


def run_chain(arm, selected, direction, seed, schedule, baseline_points, triangles, signs, baseline):
    rng = np.random.default_rng(seed)
    normalized = np.asarray(direction, dtype=float)
    normalized /= max(1.0, float(np.max(np.abs(normalized))))
    initial_direction = normalized.copy()
    if seed != 20260828 + (ord(arm) - ord("A")) * 2:
        jitter = rng.normal(0.0, 0.10, size=24)
        normalized = normalized + jitter
        normalized /= max(1.0, float(np.max(np.abs(normalized))))
    coords = np.clip(baseline_points.reshape(-1) + 0.02 * normalized, 0.0, 1.0)
    vector = np.r_[coords, baseline]
    selected_set = {tuple(tri) for tri in selected}
    stages = []
    for lam in schedule:
        raw_constraints = homotopy_constraints(vector, triangles, signs, selected_set, lam)
        feasible_t = float(max(0.0, np.min(raw_constraints / np.where(np.asarray([tuple(tri) in selected_set for tri in triangles]), max(lam, 1e-12), 1.0))))
        vector[24] = min(float(vector[24]), feasible_t * 0.999999)
        objective = lambda value: -value[24]
        constraint = {
            "type": "ineq",
            "fun": lambda value, lam=lam: homotopy_constraints(value, triangles, signs, selected_set, lam),
        }
        from scipy.optimize import minimize

        optimized = minimize(
            objective,
            vector,
            method="SLSQP",
            bounds=[(0.0, 1.0)] * 24 + [(0.0, 0.2)],
            constraints=[constraint],
            options={"maxiter": 500, "ftol": 1e-12, "disp": False},
        )
        vector = optimized.x
        minimum, active, all_areas = true_area_data(vector[:24].reshape(12, 2), triangles)
        stages.append({
            "lambda": lam,
            "optimizer_success": bool(optimized.success),
            "optimizer_status": int(optimized.status),
            "optimizer_message": str(optimized.message),
            "iterations": int(getattr(optimized, "nit", -1)),
            "relaxed_objective_lower_bound": float(vector[24]),
            "true_minimum_area_all_220": minimum,
            "true_active_triangles": active,
            "active_triangle_count": len(active),
            "coordinate_vector": [float(x) for x in vector[:24]],
            "minimum_area_gap_from_baseline": minimum - baseline,
            "min_signed_constraint": float(np.min(homotopy_constraints(vector, triangles, signs, selected_set, lam))),
            "all_areas_float64": [float(x) for x in all_areas],
        })
    final = stages[-1]
    return {
        "arm": arm,
        "seed": seed,
        "initial_direction_normalized": [float(x) for x in initial_direction / max(1.0, float(np.max(np.abs(initial_direction))))],
        "stages": stages,
        "final_coordinate_vector": final["coordinate_vector"],
        "final_true_minimum_area_all_220": final["true_minimum_area_all_220"],
        "final_true_active_triangles": final["true_active_triangles"],
        "final_active_triangle_count": final["active_triangle_count"],
    }


def run_homotopy(structural, schedule=SCHEDULE):
    baseline_points, triangles, signs, baseline = float_baseline_data()
    results = []
    for index, arm in enumerate(("A", "B", "C")):
        selected = structural["critical_orbits"][arm]
        direction = structural["relaxed_orbits"][arm]["nonzero_cone"]["direction"]
        for replicate in range(2):
            seed = 20260828 + index * 2 + replicate
            results.append(run_chain(
                arm, selected, direction, seed, schedule, baseline_points, triangles, signs, baseline
            ))
    best = max(results, key=lambda item: item["final_true_minimum_area_all_220"])
    result = {
        "experiment": "72",
        "problem_id": "heilbronn_n12",
        "target_id": "heilbronn_n12_min_area_gt_comellas_yebra",
        "optimizer": "SLSQP constrained continuation",
        "schedule": list(schedule),
        "baseline_float64": baseline,
        "baseline_points": baseline_points.tolist(),
        "true_triangle_count": len(triangles),
        "arms": results,
        "best_arm": {"arm": best["arm"], "seed": best["seed"], "final_true_minimum_area_all_220": best["final_true_minimum_area_all_220"]},
        "target_reached_float64": bool(best["final_true_minimum_area_all_220"] > baseline + 1e-8),
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--structural", action="store_true")
    parser.add_argument("--run-homotopy", action="store_true")
    parser.add_argument("--output", type=Path, default=STRUCTURAL_ARTIFACT)
    args = parser.parse_args()
    if args.structural and args.run_homotopy:
        parser.error("choose one mode")
    if args.structural:
        result = structural_audit()
    elif args.run_homotopy:
        structural_path = ROOT / "artifacts" / "heilbronn-experiment72-structural.json"
        if not structural_path.exists():
            parser.error("run --structural first")
        structural = json.loads(structural_path.read_text(encoding="utf-8"))
        result = run_homotopy(structural)
        args.output = RUN_ARTIFACT
        RUN_RAW.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    else:
        parser.error("choose --structural or --run-homotopy")
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "minimum_triangle_count": result["minimum_triangle_count"],
        "orbit_sizes": {key: len(value) for key, value in result["critical_orbits"].items()},
        "full_nonzero_feasible": result["full_active_set"]["nonzero_feasible_direction"]["feasible"],
        "full_margin": result["full_active_set"]["ascent_margin"]["common_doubled_area_derivative"],
        "relaxed": {
            key: {
                "nonzero_feasible": value["nonzero_cone"]["feasible"],
                "margin": value["ascent_margin"]["common_doubled_area_derivative"],
            }
            for key, value in result["relaxed_orbits"].items()
        },
        "output": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
