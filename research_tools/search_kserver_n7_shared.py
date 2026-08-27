#!/usr/bin/env python3
"""Single-process/shared-cache n=7 search using the pinned upstream logic."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import runpy
import time
from pathlib import Path
import random
import sys


DEFAULT_SOURCE = "/home/kserver/k-server-bench/examples/search_n7_async_pipeline/search_n7_async_pipeline.py"
DEFAULT_ARTIFACT = Path("artifacts/kserver-n7-shared-cache-001.json")


def score_full_taxi(module: dict[str, object], coefs_list: list[tuple[int, ...]], started_at: float, deadline: float) -> list[dict[str, object]]:
    if time.time() >= deadline:
        return []
    from kserver.evaluation import NumpyKServerInstance
    from kserver.evaluation.evaluation import (
        _accumulate_unique_wf,
        _unique_wf_dict,
        _unwrap_potential_result,
        _wf_key,
        batch_compute_potential_mp,
    )

    load_main_module = module["load_main_module"]
    taxi_mod = load_main_module()
    metric = module["TAXI_METRIC"]
    inst = NumpyKServerInstance.load(metric)
    context = inst.get_context()
    matrix = module["MATRIX"]
    base = taxi_mod.Potential(context, n=7, index_matrix=matrix, coefs=[0] * module["N_COEFS"])
    evaluate = module["evaluate_heavy_candidate"]
    results: list[dict[str, object]] = []
    for candidate_id, coefs in enumerate(coefs_list, start=1):
        if time.time() >= deadline:
            break
        candidate_started = time.time()
        try:
            payload = evaluate(
                taxi_mod,
                inst,
                context,
                base,
                "stage_d",
                candidate_id,
                coefs,
                1,
                None,
                _unwrap_potential_result,
                _wf_key,
                _unique_wf_dict,
                _accumulate_unique_wf,
                batch_compute_potential_mp,
            )
            payload["estimated_total_violations"] = payload["violations_k"] / payload["processed_normalized_edges_score"] if payload["processed_normalized_edges_score"] else float("inf")
            results.append({"candidate_id": candidate_id, "coefs": list(coefs), "payload": payload, "elapsed_s": time.time() - candidate_started})
        except Exception as exc:  # preserve a precise runtime failure
            results.append({"candidate_id": candidate_id, "coefs": list(coefs), "error": repr(exc), "elapsed_s": time.time() - candidate_started})
            break
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--search-seconds", type=float, default=600.0)
    parser.add_argument("--wall-seconds", type=float, default=1200.0)
    parser.add_argument("--taxi-top", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260827)
    args = parser.parse_args()

    mp.set_start_method("fork")
    started_at = time.time()
    deadline = started_at + args.wall_seconds
    source = str(args.source)
    module = runpy.run_path(source, run_name="n7_search_module")
    rng = random.Random(args.seed)
    unique: set[tuple[int, ...]] = set()
    circle_results: list[dict[str, object]] = []
    elite: list[tuple[int, ...]] = []
    error: str | None = None

    try:
        print("building one shared circle cache", flush=True)
        mod, context, distances, cache, edges = module["build_ck4_cache"]()
        print(f"circle cache shape={cache.shape} bytes={cache.nbytes}", flush=True)
        zero = tuple([0] * module["N_COEFS"])
        seeds = [zero, *[tuple(v) for v in module["SEED_VECTORS"]]]
        families = ("seed_dense", "seed_sparse", "mutate_ck4", "mutate_proxy", "mutate_timed", "mutate_full")
        search_deadline = min(deadline, started_at + args.search_seconds)
        while time.time() < search_deadline:
            if not elite:
                parent = zero
                family = rng.choice(("seed_dense", "seed_sparse"))
            else:
                parent = rng.choice(elite[: min(16, len(elite))])
                family = rng.choice(families)
            candidate = seeds.pop(0) if seeds else module["mutate_vector"](parent, rng, family)
            if candidate in unique:
                continue
            unique.add(candidate)
            score = module["evaluate_ck4_cached"](mod, context, distances, cache, edges, candidate)
            circle_results.append({"candidate_id": len(circle_results) + 1, "coefs": list(candidate), "family": family, "circle_violations": int(score)})
            elite.append(candidate)
            elite.sort(key=lambda vec: next(item["circle_violations"] for item in circle_results if tuple(item["coefs"]) == vec))
            elite = elite[:64]
            if len(circle_results) % 100 == 0:
                print(f"circle candidates={len(circle_results)} best={circle_results[-1]['circle_violations']}", flush=True)
    except Exception as exc:
        error = repr(exc)
        print(f"shared-cache failure: {error}", flush=True)

    circle_results.sort(key=lambda item: (int(item["circle_violations"]), int(item["candidate_id"])))
    selected = [tuple(item["coefs"]) for item in circle_results[: max(0, args.taxi_top)]]
    full_results: list[dict[str, object]] = []
    if error is None and selected and time.time() < deadline:
        print(f"starting sequential full taxi evaluations count={len(selected)}", flush=True)
        full_results = score_full_taxi(module, selected, started_at, deadline)

    payload = {
        "experiment_id": "kserver-n7-shared-cache-001",
        "status": "completed" if error is None else "runtime_failure",
        "started_at_unix": started_at,
        "finished_at_unix": time.time(),
        "elapsed_s": time.time() - started_at,
        "source": source,
        "seed": args.seed,
        "shared_cache": {"built": error is None, "shape": list(cache.shape) if error is None else None, "bytes": int(cache.nbytes) if error is None else None},
        "circle_search": {"unique_candidates": len(unique), "completed_candidates": len(circle_results), "best": circle_results[:20]},
        "full_taxi_results": full_results,
        "target_reached": any("payload" in item and int(item["payload"]["violations_k"]) < 3 for item in full_results),
        "error": error,
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(args.artifact, flush=True)
    return 0 if error is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
