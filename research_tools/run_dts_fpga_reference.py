#!/usr/bin/env python3
"""Compile/run the public FPGA-search C reference for the frozen DTS target.

The external source is read and transformed only in a temporary build file:
the search algorithm is retained, while the instance constants and seed are
made deterministic for the repository's (7,5), scope-111 experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time

from verify_dts import verify


REPLACEMENTS = {
    "#define n 14": "#define n 7",
    "#define k 4": "#define k 5",
    "#define M 146": "#define M 111",
    "#define TRAINING_M (152)": "#define TRAINING_M (111)",
    "unsigned long long int seed = time(NULL) ^ getpid();": "unsigned long long int seed = 20260902ULL;",
    "int main() {": "int main() {\n\tsetvbuf(stdout, NULL, _IOLBF, 0);",
}


def transform(source: str, training_scope: int, training_trials: int, block_gen_thresh: int, dts_gen_thresh: int) -> str:
    transformed = source
    replacements = dict(REPLACEMENTS)
    replacements["#define TRAINING_M (152)"] = f"#define TRAINING_M ({training_scope})"
    replacements["#define TRAINING_TRIALS 1000"] = f"#define TRAINING_TRIALS {training_trials}"
    replacements["#define BLOCK_GEN_THRESH (100)"] = f"#define BLOCK_GEN_THRESH ({block_gen_thresh})"
    replacements["#define DTS_GEN_THRESH (2*100*1000)"] = f"#define DTS_GEN_THRESH ({dts_gen_thresh})"
    for old, new in replacements.items():
        if transformed.count(old) != 1:
            raise RuntimeError(f"expected exactly one source occurrence: {old}")
        transformed = transformed.replace(old, new, 1)
    return transformed


def parse_rows(stdout: str) -> list[list[int]]:
    marker = "decoded DTS:"
    if marker not in stdout:
        return []
    tail = stdout.split(marker, 1)[1].split("decoded spectrum:", 1)[0]
    rows = []
    for line in tail.splitlines():
        values = [int(value) for value in re.findall(r"-?\d+", line)]
        if len(values) == 6:
            rows.append(values)
    return rows[:7]


def as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--training-scope", type=int, default=111)
    parser.add_argument("--training-trials", type=int, default=1000)
    parser.add_argument("--block-gen-thresh", type=int, default=100)
    parser.add_argument("--dts-gen-thresh", type=int, default=200000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    original = args.source.read_text(encoding="utf-8")
    transformed = transform(
        original,
        args.training_scope,
        args.training_trials,
        args.block_gen_thresh,
        args.dts_gen_thresh,
    )
    source_sha256 = hashlib.sha256(original.encode()).hexdigest()
    transformed_sha256 = hashlib.sha256(transformed.encode()).hexdigest()
    stdout = ""
    stderr = ""
    timed_out = False
    compile_returncode = None
    run_returncode = None
    with tempfile.TemporaryDirectory(prefix="dts-fpga-ref-") as temp_dir:
        temp = Path(temp_dir)
        source_path = temp / "dts_search_7_5.c"
        binary_path = temp / "dts-search"
        source_path.write_text(transformed, encoding="utf-8")
        compile_result = subprocess.run(
            ["gcc", "-Wall", "-Ofast", "-o", str(binary_path), str(source_path), "-lm"],
            capture_output=True,
            text=True,
            check=False,
        )
        compile_returncode = compile_result.returncode
        stderr += compile_result.stderr
        if compile_result.returncode == 0:
            process = subprocess.Popen(
                [str(binary_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, process_stderr = process.communicate(timeout=args.seconds)
                stderr += process_stderr
                run_returncode = process.returncode
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                partial_stdout = as_text(exc.stdout)
                partial_stderr = as_text(exc.stderr)
                process.kill()
                final_stdout, final_stderr = process.communicate()
                # communicate() after kill returns the complete pipe contents
                # on this Python/runtime combination; prefer it to avoid
                # duplicating the bytes already exposed by TimeoutExpired.
                stdout = as_text(final_stdout) or partial_stdout
                stderr += as_text(final_stderr) or partial_stderr
                run_returncode = process.returncode

    rows = parse_rows(stdout)
    checked = verify(rows) if len(rows) == 7 else {"valid": False, "scope": None}
    payload = {
        "method": "public-fpga-search-c-reference-adapted-to-7x6-scope-111",
        "source": str(args.source),
        "source_sha256": source_sha256,
        "transformed_source_sha256": transformed_sha256,
        "instance": {"n": 7, "k": 5, "scope_limit": 111, "training_scope": args.training_scope, "training_trials": args.training_trials, "block_gen_thresh": args.block_gen_thresh, "dts_gen_thresh": args.dts_gen_thresh},
        "seed": 20260902,
        "seconds": args.seconds,
        "compile_returncode": compile_returncode,
        "run_returncode": run_returncode,
        "timed_out": timed_out,
        "rows": rows,
        "verification": checked,
        "target_reached": bool(checked["valid"] and checked["scope"] <= 111),
        "stdout": stdout,
        "stderr": stderr,
        "elapsed_seconds": time.monotonic() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_reached": payload["target_reached"], "timed_out": timed_out, "rows": len(rows), "verification": checked, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
