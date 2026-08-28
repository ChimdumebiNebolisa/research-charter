#!/usr/bin/env python3
"""Audit deterministic samples from the full native DTS row catalogue."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from mmap import ACCESS_READ, mmap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER = struct.Struct("<IIIIQ")
RECORD = struct.Struct("<6B2xQQ")
MAGIC = 0x44545352

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_dts import verify  # noqa: E402


def sample_indices(count: int, sample_count: int) -> list[int]:
    if count < 1 or sample_count < 1:
        return []
    indices = {0, count - 1, count // 2}
    state = 0xD7A75001
    while len(indices) < min(sample_count, count):
        state = (state * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
        indices.add(state % count)
    return sorted(indices)


def row_mask(marks: tuple[int, ...]) -> tuple[int, int]:
    differences = [marks[right] - marks[left] for right in range(6) for left in range(right)]
    if len(set(differences)) != 15:
        raise AssertionError(f"duplicate differences in sampled row {marks}")
    lo = sum(1 << (difference - 1) for difference in differences if difference <= 64)
    hi = sum(1 << (difference - 65) for difference in differences if difference > 64)
    return lo, hi


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "catalogue",
        nargs="?",
        type=Path,
        default=ROOT / "artifacts" / "dts-rulers-scope111.bin",
    )
    parser.add_argument("--sample-count", type=int, default=32)
    args = parser.parse_args()

    with args.catalogue.open("rb") as handle, mmap(handle.fileno(), 0, access=ACCESS_READ) as data:
        magic, version, scope_limit, record_size, count = HEADER.unpack_from(data)
        if (magic, version, record_size) != (MAGIC, 1, RECORD.size):
            raise AssertionError("unexpected catalogue header")
        expected_size = HEADER.size + count * record_size
        if len(data) != expected_size:
            raise AssertionError(f"catalogue length mismatch: {len(data)} != {expected_size}")

        samples = []
        for index in sample_indices(count, args.sample_count):
            offset = HEADER.size + index * record_size
            fields = RECORD.unpack_from(data, offset)
            marks = tuple(fields[:6])
            lo, hi = row_mask(marks)
            verifier_result = verify([list(marks)])
            expected_partial_errors = ["expected 7 rows, got 1"]
            if verifier_result["valid"]:
                raise AssertionError(f"single-row verifier unexpectedly accepted row {index}")
            if verifier_result["errors"] != expected_partial_errors:
                raise AssertionError(f"unexpected verifier errors for row {index}: {verifier_result}")
            if (
                verifier_result["difference_count"] != 15
                or verifier_result["unique_difference_count"] != 15
                or verifier_result["duplicate_set"]
                or verifier_result["scope"] != marks[-1]
                or (fields[6], fields[7]) != (lo, hi)
            ):
                raise AssertionError(f"row-level verifier mismatch at catalogue index {index}")
            samples.append({"index": index, "marks": list(marks), "row_contract": "passed"})

    baseline = json.loads((ROOT / "artifacts" / "baselines" / "dts_scope112.json").read_text(encoding="utf-8"))
    baseline_result = verify(baseline["rows"])
    if not baseline_result["valid"]:
        raise AssertionError(f"repository DTS verifier rejected the canonical baseline: {baseline_result}")

    result = {
        "status": "passed",
        "catalogue": str(args.catalogue),
        "catalogue_scope": scope_limit,
        "catalogue_rows": count,
        "sample_count": len(samples),
        "sampling": "deterministic pseudorandom indices plus boundary and midpoint controls",
        "repository_verifier": {
            "sample_rows": "row-level arithmetic and uniqueness fields passed; full valid is intentionally false because the verifier requires seven rows",
            "canonical_scope112_baseline": baseline_result,
        },
        "samples": samples,
    }
    output = ROOT / "artifacts" / "dts-ruler-catalogue-sample-audit.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
