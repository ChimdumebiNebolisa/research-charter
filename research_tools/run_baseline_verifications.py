#!/usr/bin/env python3
"""Run and preserve the pre-registered local baseline verifications."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from verify_dts import verify as verify_dts
from verify_dts_independent import verify as verify_dts_independent
from verify_heilbronn import verify as verify_heilbronn


ROOT = Path(__file__).resolve().parents[1]


def write_text(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    dts_path = ROOT / "experiments" / "dts_7_5" / "raw" / "dts_scope112.json.txt"
    dts_rows = json.loads(dts_path.read_text(encoding="utf-8"))["rows"]
    dts_primary = verify_dts(dts_rows)
    dts_independent = verify_dts_independent(dts_rows)
    write_text(ROOT / "experiments" / "dts_7_5" / "raw" / "validator-primary.json.txt", dts_primary)
    write_text(ROOT / "experiments" / "dts_7_5" / "raw" / "validator-independent.json.txt", dts_independent)

    baseline_path = ROOT / "artifacts" / "baselines" / "heilbronn_comellas_yebra.json"
    if not baseline_path.is_file():
        subprocess.run([sys.executable, str(ROOT / "research_tools" / "generate_heilbronn_baseline.py")], check=True)
    points = json.loads(baseline_path.read_text(encoding="utf-8"))["points"]
    heilbronn_decimal = verify_heilbronn(points, precision=80)
    write_text(ROOT / "experiments" / "heilbronn_n12" / "raw" / "source-decimal-verification.json.txt", heilbronn_decimal)

    exact = subprocess.run(
        [sys.executable, str(ROOT / "research_tools" / "verify_heilbronn_exact.py")],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    (ROOT / "experiments" / "heilbronn_n12" / "raw" / "source-symbolic-verification.json.txt").write_text(
        exact.stdout + ("\n[stderr]\n" + exact.stderr if exact.stderr else ""), encoding="utf-8"
    )
    print(json.dumps({
        "dts_primary_valid": dts_primary["valid"],
        "dts_independent_valid": dts_independent["valid"],
        "heilbronn_decimal_valid": heilbronn_decimal["valid"],
        "heilbronn_symbolic_exit_code": exact.returncode,
    }, sort_keys=True))
    return 0 if dts_primary["valid"] and dts_independent["valid"] and heilbronn_decimal["valid"] and exact.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
