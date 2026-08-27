#!/usr/bin/env python3
"""Targeted local repair around a verified five-violation k-server seed."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import runpy
import time
from itertools import combinations, product
from pathlib import Path


SOURCE = "/home/kserver/k-server-bench/examples/search_n7_async_pipeline/search_n7_async_pipeline.py"
ARTIFACT = Path("artifacts/kserver-n7-targeted-mutation-001.json")
SEED_EDGE_INDEXES = [1382726, 1446816, 2930299, 5594108, 6193322]
ACTIVE_INDEXES = tuple(range(6, 21))
VALUE_SET = tuple(range(-5, 6))
DELTA_SET = (-2, -1, 1, 2)


def screen_candidate(taxi_mod, context, nodes, edges, seed_edges, coefs):
    potential = taxi_mod.Potential(context, n=7, index_matrix=taxi_mod.MATRIX, coefs=list(coefs))
    node_indexes = sorted({int(edges[i]["from"]) for i in seed_edges} | {int(edges[i]["to"]) for i in seed_edges})
    values = {}
    for node_idx in node_indexes:
        value = potential(nodes[node_idx]["wf_norm"])
        values[node_idx] = float(value[0] if isinstance(value, tuple) else value)
    violations = []
    for edge_idx in seed_edges:
        edge = edges[edge_idx]
        if taxi_mod.is_violation(values[int(edge["from"])], values[int(edge["to"])], edge["d_min"], edge["ext"], context.k):
            violations.append(int(edge_idx))
    return violations


def full_evaluate(module, coefs_list, deadline):
    from kserver.evaluation import NumpyKServerInstance
    from kserver.evaluation.evaluation import (
        _accumulate_unique_wf,
        _unique_wf_dict,
        _unwrap_potential_result,
        _wf_key,
        batch_compute_potential_mp,
    )

    taxi_mod = module["load_main_module"]()
    inst = NumpyKServerInstance.load(module["TAXI_METRIC"])
    context = inst.get_context()
    base = taxi_mod.Potential(context, n=7, index_matrix=module["MATRIX"], coefs=[0] * module["N_COEFS"])
    results = []
    for candidate_id, coefs in enumerate(coefs_list, start=1):
        if time.time() >= deadline:
            break
        started = time.time()
        try:
            payload = module["evaluate_heavy_candidate"](
                taxi_mod,
                inst,
                context,
                base,
                "stage_d",
                candidate_id,
                coefs,
                8,
                None,
                _unwrap_potential_result,
                _wf_key,
                _unique_wf_dict,
                _accumulate_unique_wf,
                batch_compute_potential_mp,
            )
            payload["estimated_total_violations"] = payload["violations_k"] / payload["processed_normalized_edges_score"] if payload["processed_normalized_edges_score"] else float("inf")
            item = {"candidate_id": candidate_id, "coefs": list(coefs), "payload": payload, "elapsed_s": time.time() - started}
            results.append(item)
            print(f"full candidate={candidate_id} violations_k={payload['violations_k']} elapsed_s={item['elapsed_s']:.1f}", flush=True)
            if int(payload["violations_k"]) < 3:
                break
        except Exception as exc:
            results.append({"candidate_id": candidate_id, "coefs": list(coefs), "error": repr(exc), "elapsed_s": time.time() - started})
            break
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--wall-seconds", type=float, default=2400.0)
    parser.add_argument("--taxi-top", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260827)
    args = parser.parse_args()
    mp.set_start_method("fork")
    started = time.time()
    deadline = started + args.wall_seconds
    module = runpy.run_path(args.source, run_name="n7_search_module")
    taxi_mod = module["load_main_module"]()
    inst = module["NumpyKServerInstance"].load(module["TAXI_METRIC"]) if "NumpyKServerInstance" in module else None
    if inst is None:
        from kserver.evaluation import NumpyKServerInstance
        inst = NumpyKServerInstance.load(module["TAXI_METRIC"])
    context = inst.get_context()
    nodes = inst.get_nodes()
    edges = inst.get_edges()
    seed = tuple(module["SEED_VECTORS"][0])
    candidates: dict[tuple[int, ...], dict[str, object]] = {seed: {"kind": "seed", "changes": []}}
    for idx in ACTIVE_INDEXES:
        for value in VALUE_SET:
            vec = list(seed)
            vec[idx] = value
            candidates.setdefault(tuple(vec), {"kind": "one_replace", "changes": [[idx, value]]})
    for i, j in combinations(ACTIVE_INDEXES, 2):
        for di, dj in product(DELTA_SET, repeat=2):
            vec = list(seed)
            vec[i] += di
            vec[j] += dj
            if vec[i] in VALUE_SET and vec[j] in VALUE_SET:
                candidates.setdefault(tuple(vec), {"kind": "two_delta", "changes": [[i, di], [j, dj]]})

    screened = []
    for number, (coefs, meta) in enumerate(candidates.items(), start=1):
        if time.time() >= deadline:
            break
        violated = screen_candidate(taxi_mod, context, nodes, edges, SEED_EDGE_INDEXES, coefs)
        screened.append({"coefs": list(coefs), "screen_violations": len(violated), "remaining_seed_edges": violated, **meta})
        if number % 250 == 0:
            print(f"screened={number} best_screen={min(x['screen_violations'] for x in screened)}", flush=True)
    screened.sort(key=lambda item: (int(item["screen_violations"]), len(item["changes"]), item["coefs"]))
    selected = [tuple(item["coefs"]) for item in screened if tuple(item["coefs"]) != seed][: max(0, args.taxi_top)]
    full_results = full_evaluate(module, selected, deadline) if selected and time.time() < deadline else []
    payload = {
        "experiment_id": "kserver-n7-targeted-mutation-001",
        "status": "completed",
        "started_at_unix": started,
        "finished_at_unix": time.time(),
        "elapsed_s": time.time() - started,
        "seed": args.seed,
        "seed_coefs": list(seed),
        "seed_edge_indexes": SEED_EDGE_INDEXES,
        "neighborhood_generated": len(candidates),
        "screened_candidates": len(screened),
        "screen_top": screened[:25],
        "selected_for_full_taxi": [list(x) for x in selected],
        "full_taxi_results": full_results,
        "target_reached": any("payload" in x and int(x["payload"]["violations_k"]) < 3 for x in full_results),
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(args.artifact, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
