#!/usr/bin/env python3
"""Screen a translation-invariant work-function spread correction on circle m=6."""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import time
from pathlib import Path


DEFAULT_SOURCE = "/home/kserver/k-server-bench/examples/search_n7_async_pipeline/search_n7_async_pipeline.py"
DEFAULT_METRIC = "/home/kserver/k-server-bench/metrics/circle_k4_m6.pickle"
DEFAULT_ARTIFACT = Path("artifacts/kserver-n7-range-correction-001.json")
DEFAULT_RAW = Path("experiments/kserver_k4_circle/raw/kserver-n7-range-correction-001.txt")
SEED = (0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, -1, -1, 0, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--metric", default=DEFAULT_METRIC)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--experiment-id", default="kserver-n7-range-correction-001")
    args = parser.parse_args()

    started = time.time()
    module = runpy.run_path(args.source, run_name="n7_search_module")
    mod = module["load_main_module"]()
    instance = mod.NumpyKServerInstance.load(args.metric)
    context = instance.get_context()
    potential = mod.Potential(context, n=7, index_matrix=module["MATRIX"], coefs=list(SEED))
    nodes = instance.get_nodes()
    edges = instance.get_edges()
    canonical_values = []
    spreads = []
    for node in nodes:
        value = potential(node["wf_norm"])
        if isinstance(value, tuple):
            value = value[0]
        wf = node["wf_norm"]
        canonical_values.append(float(value))
        spreads.append(float(max(wf) - min(wf)))

    alphas = [-8.0, -4.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 4.0, 8.0]
    scores = []
    for alpha in alphas:
        values = [base + alpha * spread for base, spread in zip(canonical_values, spreads)]
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
                "alpha": alpha,
                "violations_k": len(violated),
                "edges_total": len(edges),
                "violated_edge_idxes": violated,
            }
        )

    payload = {
        "experiment_id": args.experiment_id,
        "status": "completed",
        "started_at_unix": started,
        "finished_at_unix": time.time(),
        "elapsed_s": time.time() - started,
        "source": args.source,
        "metric": args.metric,
        "candidate_family": "canonical seed potential plus alpha*(max(wf_norm)-min(wf_norm))",
        "coefs": list(SEED),
        "nodes": len(nodes),
        "edges": len(edges),
        "scores": scores,
        "best_circle_score": min(scores, key=lambda item: (item["violations_k"], abs(item["alpha"]))),
        "target_reached": False,
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    input_hash = hashlib.sha256(args.artifact.read_bytes()).hexdigest().upper()
    report = [
        "Experiment kserver-n7-range-correction-001 execution record",
        f"Metric: {args.metric}; nodes={len(nodes)} edges={len(edges)}",
        "Candidate family: canonical seed potential plus alpha*(max(wf_norm)-min(wf_norm))",
        f"Scores: {json.dumps(scores, sort_keys=True)}",
        f"Artifact SHA256: {input_hash}",
    ]
    args.raw.parent.mkdir(parents=True, exist_ok=True)
    args.raw.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"best_circle_score": payload["best_circle_score"], "artifact": str(args.artifact)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
