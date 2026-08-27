#!/usr/bin/env python3
"""Screen normalized entropic soft-min potentials on the complete circle metric."""

from __future__ import annotations

import argparse
import json
import runpy
import time
from pathlib import Path

import numpy as np


SOURCE = "/home/kserver/k-server-bench/examples/search_n7_async_pipeline/search_n7_async_pipeline.py"
DEFAULT_ARTIFACT = Path("artifacts/kserver-n7-softmin-001.json")
DEFAULT_RAW = Path("experiments/kserver_k4_circle/raw/kserver-n7-softmin-001.txt")
TEMPERATURES = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--metric", default="/home/kserver/k-server-bench/metrics/circle_k4_m6.pickle")
    args = parser.parse_args()
    started = time.time()

    module = runpy.run_path(args.source, run_name="n7_softmin_screen")
    mod = module["load_main_module"]()
    instance = module["NumpyKServerInstance"].load(args.metric)
    context = instance.get_context()
    nodes = instance.get_nodes()
    edges = instance.get_edges()
    matrix = module["MATRIX"]
    seed = list(module["SEED_VECTORS"][0])
    base = mod.Potential(context, n=7, index_matrix=matrix, coefs=seed)

    values = {temperature: np.empty(len(nodes), dtype=np.float64) for temperature in TEMPERATURES}
    hard_values = np.empty(len(nodes), dtype=np.float64)
    for node_idx, node in enumerate(nodes):
        energies = np.asarray(base._compute_candidate_values(node["wf_norm"]), dtype=np.int64)
        minimum = int(energies.min())
        hard_values[node_idx] = minimum
        counts = np.bincount(energies - minimum)
        offsets = np.arange(counts.size, dtype=np.float64)
        for temperature in TEMPERATURES:
            weights = counts.astype(np.float64) * np.exp(-offsets / temperature)
            log_mean = np.log(float(weights.sum())) - np.log(float(energies.size))
            values[temperature][node_idx] = minimum - temperature * log_mean

    results = []
    hard_violations = []
    for edge_idx, edge in enumerate(edges):
        if mod.is_violation(
            float(hard_values[int(edge["from"])]),
            float(hard_values[int(edge["to"])]),
            edge["d_min"],
            edge["ext"],
            context.k,
        ):
            hard_violations.append(edge_idx)
    results.append({"variant": "hard_min_control", "temperature": None, "violations_k": len(hard_violations), "edges_total": len(edges), "violated_edge_idxes": hard_violations})

    for temperature in TEMPERATURES:
        violated = []
        current = values[temperature]
        for edge_idx, edge in enumerate(edges):
            if mod.is_violation(
                float(current[int(edge["from"])]),
                float(current[int(edge["to"])]),
                edge["d_min"],
                edge["ext"],
                context.k,
            ):
                violated.append(edge_idx)
        results.append({"variant": "normalized_entropic_softmin", "temperature": temperature, "violations_k": len(violated), "edges_total": len(edges), "violated_edge_idxes": violated, "potential_kwargs": {"n": 7, "index_matrix": matrix, "coefs": seed, "temperature": temperature}})
        print(f"temperature={temperature} circle_violations={len(violated)}", flush=True)

    results.sort(key=lambda item: (int(item["violations_k"]), float(item["temperature"] or 0.0)))
    payload = {
        "experiment_id": "kserver-n7-softmin-001",
        "status": "completed",
        "metric": args.metric,
        "nodes": len(nodes),
        "edges": len(edges),
        "seed_coefs": seed,
        "temperatures": list(TEMPERATURES),
        "results": results,
        "best_circle_result": results[0],
        "target_reached": any(int(item["violations_k"]) < 3 for item in results),
        "elapsed_s": time.time() - started,
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.raw.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    args.raw.write_text(
        "\n".join([
            "Experiment kserver-n7-softmin-001",
            f"Metric: {args.metric}; nodes={len(nodes)} edges={len(edges)}",
            "Candidate family: normalized entropic soft-min of canonical configuration energies",
            f"Temperatures: {list(TEMPERATURES)}",
            f"Scores: {[(item['variant'], item['temperature'], item['violations_k']) for item in results]}",
            f"Best result: {results[0]}",
            f"Elapsed seconds: {payload['elapsed_s']}",
        ]) + "\n",
        encoding="utf-8",
    )
    print(args.artifact, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
