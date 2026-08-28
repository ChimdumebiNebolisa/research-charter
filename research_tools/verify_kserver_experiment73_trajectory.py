"""Independent full-metric audit of the completed Experiment 73 trajectory."""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "research_tools" / "synthesize_kserver_experiment73.py"
RUN = ROOT / "artifacts" / "kserver-experiment73-synthesis-resumed.json"
OUTPUT = ROOT / "artifacts" / "kserver-experiment73-trajectory-verification.json"


def load_synthesizer():
    spec = importlib.util.spec_from_file_location("e73_trajectory_verify", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def reference_correction(features: np.ndarray, mode: str, branches):
    values = np.column_stack([
        branch[0] + features @ np.asarray(branch[1:], dtype=float)
        for branch in branches
    ])
    values = np.column_stack([np.zeros(len(features)), values])
    return np.max(values, axis=1) if mode == "max" else np.min(values, axis=1)


def audit(metric, mode: str, branches):
    values = metric.base + reference_correction(metric.features, mode, branches)
    slack = values[metric.edge_to] - values[metric.edge_from] - metric.edge_weights
    return {
        "violations": int(np.count_nonzero(slack < 0)),
        "min_slack": float(np.min(slack)),
        "potential_min": float(np.min(values)),
        "potential_max": float(np.max(values)),
    }


def main() -> int:
    started = time.perf_counter()
    run = json.loads(RUN.read_text(encoding="utf-8"))
    m = load_synthesizer()
    cache = np.load(m.TAXI_CACHE)
    taxi = m.load_metric("circle_taxi_k4_m6.pickle", cache["canonical"])
    circle = m.load_metric("circle_k4_m6.pickle")
    metrics = {taxi.name: taxi, circle.name: circle}
    checked = []
    for entry in run["trajectory"]:
        branches = tuple(tuple(branch) for branch in entry["branches"])
        for name, metric in metrics.items():
            expected = entry["taxi_audit" if name == taxi.name else "circle_audit"]
            actual = audit(metric, entry["complexity"].rsplit("_", 1)[1], branches)
            if actual["violations"] != expected["violations"] or not np.isclose(actual["min_slack"], expected["min_slack"], rtol=0.0, atol=1e-12):
                raise AssertionError(f"trajectory mismatch for {entry['complexity']} {name}: {actual} != {expected}")
        checked.append({
            "complexity": entry["complexity"],
            "iteration": entry["iteration"],
            "taxi_violations": entry["taxi_audit"]["violations"],
            "circle_violations": entry["circle_audit"]["violations"],
            "taxi_min_slack": entry["taxi_audit"]["min_slack"],
            "circle_min_slack": entry["circle_audit"]["min_slack"],
        })
    result = {
        "status": "passed",
        "trajectory_entries_checked": len(checked),
        "metrics": {name: len(metric.edge_weights) for name, metric in metrics.items()},
        "checks": ["full taxi violation counts", "full circle violation counts", "taxi minimum slack", "circle minimum slack"],
        "trajectory": checked,
        "elapsed_seconds": time.perf_counter() - started,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
