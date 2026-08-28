"""Deterministic performance gate for the repaired Experiment 73 scorer."""

from __future__ import annotations

import gc
import importlib.util
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "research_tools" / "synthesize_kserver_experiment73.py"
EQUIVALENCE = ROOT / "artifacts" / "kserver-experiment73-equivalence.json"
OUTPUT = ROOT / "artifacts" / "kserver-experiment73-performance.json"


def load_synthesizer():
    spec = importlib.util.spec_from_file_location("e73_benchmark", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def rss_mb() -> float | None:
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except ImportError:
        return None


def main() -> int:
    started = time.perf_counter()
    m = load_synthesizer()
    cache = np.load(m.TAXI_CACHE)
    taxi = m.load_metric("circle_taxi_k4_m6.pickle", cache["canonical"])
    circle = m.load_metric("circle_k4_m6.pickle")
    metrics = {taxi.name: taxi, circle.name: circle}
    active = {
        taxi.name: {4766035, 5594108, 6193322} | set(np.argsort(taxi.base_slack)[:128].tolist()),
        circle.name: set(range(len(circle.base_slack))),
    }
    rows = m.active_arrays(active, metrics)
    initial = {
        "taxi_active_edges": len(active[taxi.name]),
        "circle_active_edges": len(active[circle.name]),
        "taxi_total_edges": len(taxi.edge_weights),
        "circle_total_edges": len(circle.edge_weights),
    }
    equivalence = json.loads(EQUIVALENCE.read_text(encoding="utf-8"))
    gc.collect()
    before_rss = rss_mb()
    tracemalloc.start()
    t0 = time.perf_counter()
    best = m.best_single(rows, "max")
    one_branch_seconds = time.perf_counter() - t0
    current, peak_trace = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    after_rss = rss_mb()
    multi_seconds = {}
    for branch_count, pool_count in ((2, 32), (3, 24)):
        t0 = time.perf_counter()
        m.best_multi(rows, "max", branch_count, pool_count)
        multi_seconds[f"{branch_count}-branch_max"] = time.perf_counter() - t0
    full_config_steps = 24
    estimated_seconds = full_config_steps * max([one_branch_seconds, *multi_seconds.values()])
    result = {
        "status": "passed" if equivalence.get("status") == "passed" else "blocked_equivalence",
        "equivalence_status": equivalence.get("status"),
        "initial_active_set": initial,
        "one_branch_max": {
            "branches": len(m.BRANCH_GRID),
            "wall_seconds": one_branch_seconds,
            "candidates_per_second": len(m.BRANCH_GRID) / one_branch_seconds,
            "best_branch": list(best),
        },
        "multi_branch_max_wall_seconds": multi_seconds,
        "memory": {
            "rss_before_mb": before_rss,
            "rss_after_mb": after_rss,
            "rss_delta_mb": None if before_rss is None or after_rss is None else after_rss - before_rss,
            "tracemalloc_peak_mb": peak_trace / 1024 / 1024,
        },
        "estimated_full_declared_configuration_seconds": estimated_seconds,
        "declared_wall_time_seconds": m.SCIENTIFIC_WALL_TIME,
        "overall_elapsed_seconds": time.perf_counter() - started,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
