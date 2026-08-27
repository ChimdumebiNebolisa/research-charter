#!/usr/bin/env python3
"""Screen structured index_matrix variants on the complete circle m=6 metric."""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import time
from pathlib import Path


DEFAULT_SOURCE = "/home/kserver/k-server-bench/examples/search_n7_async_pipeline/search_n7_async_pipeline.py"
DEFAULT_METRIC = "/home/kserver/k-server-bench/metrics/circle_k4_m6.pickle"
DEFAULT_ARTIFACT = Path("artifacts/kserver-n7-index-matrix-screen-001.json")
DEFAULT_RAW = Path("experiments/kserver_k4_circle/raw/kserver-n7-index-matrix-screen-001.txt")
SEED = (0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, -1, -1, 0, 0)
BASE_MATRIX = [
    [-1, -1, -1, -1],
    [1, -2, -3, -4],
    [1, 2, -5, -6],
    [1, 3, 5, -7],
    [1, 4, 6, 7],
]


def relabel(matrix: list[list[int]], shift: int) -> list[list[int]]:
    def map_token(token: int) -> int:
        sign = -1 if token < 0 else 1
        absolute = abs(token)
        mapped = ((absolute - 1 + shift) % 7) + 1
        return sign * mapped

    return [[map_token(token) for token in row] for row in matrix]


def build_variants() -> list[dict[str, object]]:
    variants: list[dict[str, object]] = [{"variant_id": "base_control", "matrix": BASE_MATRIX}]
    seen = {tuple(tuple(row) for row in BASE_MATRIX)}
    for token in list(range(-7, 0)) + list(range(1, 8)):
        matrix = [row[:] for row in BASE_MATRIX]
        matrix[0] = [token] * 4
        key = tuple(tuple(row) for row in matrix)
        if key not in seen:
            seen.add(key)
            variants.append({"variant_id": f"row0_uniform_{token:+d}", "matrix": matrix})
    for shift in (1, 2, 3, 4, 5, 6):
        matrix = relabel(BASE_MATRIX, shift)
        key = tuple(tuple(row) for row in matrix)
        if key not in seen:
            seen.add(key)
            variants.append({"variant_id": f"global_cyclic_relabel_{shift}", "matrix": matrix})
    return variants


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--metric", default=DEFAULT_METRIC)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--experiment-id", default="kserver-n7-index-matrix-screen-001")
    args = parser.parse_args()

    started = time.time()
    module = runpy.run_path(args.source, run_name="n7_search_module")
    mod = module["load_main_module"]()
    instance = mod.NumpyKServerInstance.load(args.metric)
    context = instance.get_context()
    nodes = instance.get_nodes()
    edges = instance.get_edges()
    scores: list[dict[str, object]] = []
    for variant in build_variants():
        matrix = variant["matrix"]
        potential = mod.Potential(context, n=7, index_matrix=matrix, coefs=list(SEED))
        values = []
        for node in nodes:
            value = potential(node["wf_norm"])
            if isinstance(value, tuple):
                value = value[0]
            values.append(float(value))
        violated = []
        for edge_idx, edge in enumerate(edges):
            if mod.is_violation(
                values[int(edge["from"])],
                values[int(edge["to"])],
                edge["d_min"],
                edge["ext"],
                context.k,
            ):
                violated.append(edge_idx)
        scores.append(
            {
                "variant_id": variant["variant_id"],
                "matrix": matrix,
                "violations_k": len(violated),
                "edges_total": len(edges),
                "violated_edge_idxes": violated,
            }
        )
        print(f"{variant['variant_id']}: circle violations={len(violated)}", flush=True)
        del potential, values

    scores.sort(key=lambda item: (int(item["violations_k"]), str(item["variant_id"])))
    payload = {
        "experiment_id": args.experiment_id,
        "status": "completed",
        "started_at_unix": started,
        "finished_at_unix": time.time(),
        "elapsed_s": time.time() - started,
        "source": args.source,
        "metric": args.metric,
        "coefs": list(SEED),
        "screen_family": "row-0 signed uniform anchors plus global cyclic relabels of the five-row index matrix",
        "nodes": len(nodes),
        "edges": len(edges),
        "variants_tested": len(scores),
        "scores": scores,
        "circle_feasible_variants": [item for item in scores if int(item["violations_k"]) == 0],
        "target_reached": False,
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact_hash = hashlib.sha256(args.artifact.read_bytes()).hexdigest().upper()
    report = [
        "Experiment kserver-n7-index-matrix-screen-001 execution record",
        f"Metric: {args.metric}; nodes={len(nodes)} edges={len(edges)}",
        f"Variants tested: {len(scores)}",
        f"Scores: {json.dumps([(x['variant_id'], x['violations_k']) for x in scores])}",
        f"Circle-feasible variants: {json.dumps([x['variant_id'] for x in payload['circle_feasible_variants']])}",
        f"Artifact SHA256: {artifact_hash}",
    ]
    args.raw.parent.mkdir(parents=True, exist_ok=True)
    args.raw.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"variants_tested": len(scores), "circle_feasible": len(payload["circle_feasible_variants"]), "artifact": str(args.artifact)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
