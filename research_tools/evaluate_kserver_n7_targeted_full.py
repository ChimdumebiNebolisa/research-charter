#!/usr/bin/env python3
"""Exact full taxi evaluation of finalists selected by targeted edge repair."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import runpy
import time
from pathlib import Path


SOURCE = "/home/kserver/k-server-bench/examples/search_n7_async_pipeline/search_n7_async_pipeline.py"
SCREEN_ARTIFACT = Path("artifacts/kserver-n7-targeted-mutation-001.json")
ARTIFACT = Path("artifacts/kserver-n7-targeted-full-001.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--screen-artifact", type=Path, default=SCREEN_ARTIFACT)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--wall-seconds", type=float, default=1800.0)
    parser.add_argument("--top", type=int, default=2)
    args = parser.parse_args()
    mp.set_start_method("fork")
    started = time.time()
    deadline = started + args.wall_seconds
    module = runpy.run_path(args.source, run_name="n7_search_module")
    screen = json.loads(args.screen_artifact.read_text(encoding="utf-8"))
    coefs_list = [tuple(item["coefs"]) for item in screen["screen_top"][: max(0, args.top)]]
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
        candidate_started = time.time()
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
            item = {"candidate_id": candidate_id, "coefs": list(coefs), "payload": payload, "elapsed_s": time.time() - candidate_started}
            results.append(item)
            print(f"full candidate={candidate_id} violations_k={payload['violations_k']} elapsed_s={item['elapsed_s']:.1f}", flush=True)
            if int(payload["violations_k"]) < 3:
                break
        except Exception as exc:
            results.append({"candidate_id": candidate_id, "coefs": list(coefs), "error": repr(exc), "elapsed_s": time.time() - candidate_started})
            break
    output = {"experiment_id": "kserver-n7-targeted-full-001", "status": "completed", "started_at_unix": started, "finished_at_unix": time.time(), "elapsed_s": time.time() - started, "source_screen_artifact": str(args.screen_artifact), "finalists": [list(x) for x in coefs_list], "full_taxi_results": results, "target_reached": any("payload" in x and int(x["payload"]["violations_k"]) < 3 for x in results)}
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(args.artifact, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
