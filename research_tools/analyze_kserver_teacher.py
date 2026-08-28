"""Analyze the finite taxi teacher against the canonical potential.

The analysis is deliberately feature-oriented: it computes only statistics that
can be evaluated from a work function and the pinned metric context, never node
IDs or frozen table indices.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "artifacts" / "upstream-cache" / "k-server-bench"
sys.path.insert(0, str(UPSTREAM / "k-servers" / "src"))
sys.path.insert(0, str(ROOT / "research_tools" / "compat"))

from kserver.evaluation import NumpyKServerInstance
from kserver.potential.canonical_potential import Potential as CanonicalPotential


INDEX_MATRIX = [
    [-5, -5, -5, -5],
    [5, -1, -2, -2],
    [5, 1, 3, 4],
    [5, 2, -4, -4],
    [5, 2, 4, -3],
]
COEFS = [-1, 0, -1, 0, 1, 0, 0, -1, 0, 0]
TAXI_METRIC = UPSTREAM / "metrics" / "circle_taxi_k4_m6.pickle"
TABLE = ROOT / "artifacts" / "kserver-finite-difference-relaxation-001-drop_none.npz"
OUTPUT = ROOT / "artifacts" / "kserver-experiment73-teacher-analysis.json"
CACHE = ROOT / "artifacts" / "kserver-experiment73-teacher-cache.npz"


def row_key(row: np.ndarray) -> bytes:
    return np.rint(np.asarray(row, dtype=float)).astype(np.int8).tobytes()


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    sx = float(np.std(x))
    sy = float(np.std(y))
    return 0.0 if sx == 0.0 or sy == 0.0 else float(np.corrcoef(x, y)[0, 1])


def feature_matrix(wfs: np.ndarray, canonical: np.ndarray, second: np.ndarray, argmin: np.ndarray) -> tuple[np.ndarray, list[str]]:
    minimum = np.min(wfs, axis=1)
    maximum = np.max(wfs, axis=1)
    sums = np.sum(wfs, axis=1)
    squares = np.sum(wfs * wfs, axis=1)
    counts_at_max = np.sum(wfs == maximum[:, None], axis=1)
    return np.column_stack([
        canonical,
        second - canonical,
        maximum,
        sums,
        squares,
        counts_at_max,
        argmin,
    ]), ["canonical", "canonical_second_gap", "wf_max", "wf_sum", "wf_sum_squares", "wf_count_at_max", "canonical_argmin"]


def transformed_row(row: np.ndarray, config_index: dict[tuple[int, ...], int], mode: str, offset: int) -> np.ndarray:
    def transform(point: int) -> int:
        if mode == "rotation":
            return (point + offset) % 6
        return (-point + offset) % 6

    out = np.empty_like(row)
    for config, index in config_index.items():
        mapped = tuple(sorted(transform(point) for point in config))
        out[config_index[mapped]] = row[index]
    return out


def main() -> int:
    started = time.time()
    instance = NumpyKServerInstance.load(TAXI_METRIC)
    table_payload = np.load(TABLE)
    wfs = np.asarray(instance.node_wf_norm)
    table_rows = np.asarray(table_payload["node_wf_norm"])
    teacher = np.asarray(table_payload["potential"], dtype=np.int64)
    if not np.array_equal(wfs, table_rows):
        raise ValueError("teacher rows do not match taxi metric rows")

    cache = np.load(CACHE) if CACHE.exists() else None
    if cache is not None and np.array_equal(cache["wfs"], wfs):
        canonical = np.asarray(cache["canonical"], dtype=np.int64)
        second = np.asarray(cache["second"], dtype=np.int64)
        argmin = np.asarray(cache["argmin"], dtype=np.int64)
    else:
        potential = CanonicalPotential(instance.get_context(), n=5, index_matrix=INDEX_MATRIX, coefs=COEFS)
        canonical = np.empty(len(wfs), dtype=np.int64)
        second = np.empty(len(wfs), dtype=np.int64)
        argmin = np.empty(len(wfs), dtype=np.int64)
        for index, row in enumerate(wfs):
            candidate_values = np.asarray(potential._compute_candidate_values(row), dtype=np.int64)
            order = np.partition(candidate_values, 1)
            canonical[index] = int(order[0])
            second[index] = int(order[1])
            argmin[index] = int(np.argmin(candidate_values))
        np.savez_compressed(CACHE, wfs=wfs, canonical=canonical, second=second, argmin=argmin)

    residual = teacher - canonical
    features, feature_names = feature_matrix(wfs, canonical, second, argmin)
    correlations = {name: pearson(residual, features[:, column]) for column, name in enumerate(feature_names)}
    x = np.column_stack([np.ones(len(features)), features[:, :6]])
    coefficients, *_ = np.linalg.lstsq(x, residual, rcond=None)
    fitted = x @ coefficients
    residual_r2 = 1.0 - float(np.sum((residual - fitted) ** 2) / np.sum((residual - np.mean(residual)) ** 2))

    configs = [tuple(config) for config in instance.get_context()._idx_to_config]
    config_index = {config: index for index, config in enumerate(configs)}
    group_inverses = []
    for mode in ("rotation", "reflection"):
        for offset in range(6):
            mapping = []
            for config in configs:
                if mode == "rotation":
                    mapped = tuple(sorted((point + offset) % 6 for point in config))
                else:
                    mapped = tuple(sorted((-point + offset) % 6 for point in config))
                mapping.append(config_index[mapped])
            group_inverses.append(np.argsort(np.asarray(mapping, dtype=int)))
    unique_wfs, unique_first_indices = np.unique(wfs, axis=0, return_index=True)
    row_lookup = {row_key(row): index for index, row in enumerate(unique_wfs)}
    orbit_sizes = Counter()
    orbit_residuals: dict[str, list[int]] = defaultdict(list)
    visited: set[bytes] = set()
    missing_transforms = 0
    for row in unique_wfs:
        key = row_key(row)
        if key in visited:
            continue
        orbit_keys: set[bytes] = set()
        for inverse in group_inverses:
            transformed_key = row_key(row[inverse])
            orbit_keys.add(transformed_key)
            if transformed_key not in row_lookup:
                missing_transforms += 1
        present_indices = [row_lookup[key] for key in orbit_keys if key in row_lookup]
        visited.update(orbit_keys)
        size = len(present_indices)
        orbit_sizes[size] += 1
        orbit_residuals[str(size)].extend(int(residual[unique_first_indices[j]]) for j in present_indices)

    residual_distribution = Counter(int(value) for value in residual)
    quantiles = {str(q): float(np.quantile(residual, q)) for q in (0.0, 0.01, 0.1, 0.5, 0.9, 0.99, 1.0)}
    residual_edge_indexes = [4766035, 5594108, 6193322]
    edge_context = []
    weights = np.rint(instance.edge_ext - (instance.k + 1) * instance.edge_d_min).astype(np.int64)
    for edge_index in residual_edge_indexes:
        source = int(instance.edge_from[edge_index])
        target = int(instance.edge_to[edge_index])
        edge_context.append({
            "edge_index": edge_index,
            "from_node": source,
            "to_node": target,
            "weight": int(weights[edge_index]),
            "canonical_from": int(canonical[source]),
            "canonical_to": int(canonical[target]),
            "teacher_from": int(teacher[source]),
            "teacher_to": int(teacher[target]),
            "residual_from": int(residual[source]),
            "residual_to": int(residual[target]),
            "from_wf_max": int(np.max(wfs[source])),
            "to_wf_max": int(np.max(wfs[target])),
            "from_wf_sum": int(np.sum(wfs[source])),
            "to_wf_sum": int(np.sum(wfs[target])),
        })

    result = {
        "status": "completed",
        "method": "teacher_residual_and_metric_general_feature_analysis",
        "upstream_commit": "aea64346b846c967e4448f098d4b8b1748504d27",
        "metric": TAXI_METRIC.name,
        "nodes": int(len(wfs)),
        "teacher_range": [int(np.min(teacher)), int(np.max(teacher))],
        "canonical_range": [int(np.min(canonical)), int(np.max(canonical))],
        "residual_range": [int(np.min(residual)), int(np.max(residual))],
        "residual_distribution": {str(key): int(value) for key, value in sorted(residual_distribution.items())},
        "residual_quantiles": quantiles,
        "feature_names": feature_names,
        "residual_feature_correlations": correlations,
        "six_feature_affine_residual_r2": residual_r2,
        "symmetry_orbits": {
            "group": "D6 rotations and reflections on six circle positions",
            "orbit_size_histogram": {str(key): int(value) for key, value in sorted(orbit_sizes.items())},
            "mean_residual_by_orbit_size": {key: float(np.mean(values)) for key, values in orbit_residuals.items()},
            "std_residual_by_orbit_size": {key: float(np.std(values)) for key, values in orbit_residuals.items()},
            "missing_transformed_rows": int(missing_transforms),
        },
        "residual_edge_context": edge_context,
        "elapsed_seconds": time.time() - started,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    print(OUTPUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
