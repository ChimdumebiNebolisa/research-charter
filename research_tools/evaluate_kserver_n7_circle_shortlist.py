#!/usr/bin/env python3
"""Exact taxi gate for preserved non-seed circle finalists."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import runpy
import time
from pathlib import Path

from search_kserver_n7_shared import score_full_taxi


DEFAULT_SOURCE = "/home/kserver/k-server-bench/examples/search_n7_async_pipeline/search_n7_async_pipeline.py"
DEFAULT_INPUT = Path("artifacts/kserver-n7-circle-to-taxi-001.json")
DEFAULT_ARTIFACT = Path("artifacts/kserver-n7-circle-shortlist-001.json")
DEFAULT_RAW = Path("experiments/kserver_k4_circle/raw/kserver-n7-circle-shortlist-001.txt")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--wall-seconds", type=float, default=1600.0)
    parser.add_argument("--top", type=int, default=2)
    parser.add_argument("--nested-processes", type=int, default=8)
    parser.add_argument("--experiment-id", default="kserver-n7-circle-shortlist-001")
    args = parser.parse_args()

    mp.set_start_method("fork")
    started_at = time.time()
    input_bytes = args.input.read_bytes()
    input_sha256 = hashlib.sha256(input_bytes).hexdigest().upper()
    prior = json.loads(input_bytes)
    module = runpy.run_path(args.source, run_name="n7_search_module")
    zero = tuple([0] * module["N_COEFS"])
    pinned_seeds = {tuple(v) for v in module["SEED_VECTORS"]}
    excluded = pinned_seeds | {zero}
    preserved = [
        item
        for item in prior["circle_search"]["best"]
        if tuple(item["coefs"]) not in excluded
    ]
    selected = preserved[: max(0, args.top)]
    coefs = [tuple(item["coefs"]) for item in selected]
    deadline = started_at + args.wall_seconds
    error = None
    results = []
    try:
        print(
            f"selected {len(selected)} preserved non-seed candidates from "
            f"{args.input} (sha256={input_sha256})",
            flush=True,
        )
        for item in selected:
            print(
                f"candidate_id={item['candidate_id']} circle_violations={item['circle_violations']} "
                f"family={item['family']}",
                flush=True,
            )
        results = score_full_taxi(
            module,
            coefs,
            started_at,
            deadline,
            n_processes=args.nested_processes,
        )
    except Exception as exc:  # preserve a precise runtime failure
        error = repr(exc)
        print(f"shortlist failure: {error}", flush=True)

    payload = {
        "experiment_id": args.experiment_id,
        "status": "completed" if error is None else "runtime_failure",
        "started_at_unix": started_at,
        "finished_at_unix": time.time(),
        "elapsed_s": time.time() - started_at,
        "source": args.source,
        "input_artifact": str(args.input),
        "input_artifact_sha256": input_sha256,
        "shortlist_policy": "take highest-ranked preserved circle finalists after excluding zero and every pinned SEED_VECTORS entry",
        "excluded_pinned_seed_count": len(pinned_seeds),
        "selected_candidates": selected,
        "full_taxi_results": results,
        "target_reached": any(
            "payload" in item and int(item["payload"]["violations_k"]) < 3
            for item in results
        ),
        "error": error,
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    report = [
        "Experiment kserver-n7-circle-shortlist-001 execution record",
        f"Input artifact: {args.input} (SHA256 {input_sha256})",
        "Selection: highest-ranked preserved non-seed circle finalists; zero and all five pinned seeds excluded",
        f"Selected: {json.dumps(selected, sort_keys=True)}",
        f"Full taxi results: {json.dumps(results, sort_keys=True)}",
        f"Target reached: {payload['target_reached']}",
        f"Artifact: {args.artifact}",
    ]
    args.raw.parent.mkdir(parents=True, exist_ok=True)
    args.raw.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(args.artifact, flush=True)
    return 0 if error is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
