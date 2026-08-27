#!/usr/bin/env python3
"""Run one exact pinned taxi baseline through bounded streaming workers."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import runpy
import time
from pathlib import Path


SOURCE = "/home/kserver/k-server-bench/examples/search_n7_async_pipeline/search_n7_async_pipeline.py"
ARTIFACT = Path("artifacts/kserver-n7-streaming-mp-001.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--nested-processes", type=int, default=8)
    args = parser.parse_args()
    mp.set_start_method("fork")
    started = time.time()
    module = runpy.run_path(args.source, run_name="n7_search_module")
    try:
        from kserver.evaluation.evaluation import (
            _accumulate_unique_wf,
            _unique_wf_dict,
            _unwrap_potential_result,
            _wf_key,
            batch_compute_potential_mp,
        )
        from kserver.evaluation import NumpyKServerInstance

        taxi_mod = module["load_main_module"]()
        inst = NumpyKServerInstance.load(module["TAXI_METRIC"])
        context = inst.get_context()
        base = taxi_mod.Potential(context, n=7, index_matrix=module["MATRIX"], coefs=[0] * module["N_COEFS"])
        coefs = tuple(module["SEED_VECTORS"][0])
        print(f"starting exact taxi baseline nested_processes={args.nested_processes}", flush=True)
        payload = module["evaluate_heavy_candidate"](
            taxi_mod,
            inst,
            context,
            base,
            "stage_d",
            1,
            coefs,
            max(1, args.nested_processes),
            None,
            _unwrap_potential_result,
            _wf_key,
            _unique_wf_dict,
            _accumulate_unique_wf,
            batch_compute_potential_mp,
        )
        payload["estimated_total_violations"] = payload["violations_k"] / payload["processed_normalized_edges_score"] if payload["processed_normalized_edges_score"] else float("inf")
        result = {"status": "completed", "coefs": list(coefs), "payload": payload, "elapsed_s": time.time() - started}
    except Exception as exc:
        result = {"status": "runtime_failure", "error": repr(exc), "elapsed_s": time.time() - started}
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(args.artifact, flush=True)
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
