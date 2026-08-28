"""Independent simple Python reference for the native DTS row enumerator."""

from __future__ import annotations

import itertools
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "dts-ruler-enumerator-validation.json"
HEADER = struct.Struct("<IIIIQ")
RECORD = struct.Struct("<6B2xQQ")


def reference_rows(scope_limit: int):
    rows = []
    for positive in itertools.combinations(range(1, scope_limit + 1), 5):
        marks = (0,) + positive
        differences = [marks[j] - marks[i] for i in range(6) for j in range(i + 1, 6)]
        if len(set(differences)) != 15:
            continue
        lo = sum(1 << (difference - 1) for difference in differences if difference <= 64)
        hi = sum(1 << (difference - 65) for difference in differences if difference > 64)
        rows.append((marks, lo, hi))
    return rows


def native_rows(path: Path):
    data = path.read_bytes()
    magic, version, scope_limit, record_size, count = HEADER.unpack_from(data)
    if magic != 0x44545352 or version != 1 or record_size != RECORD.size:
        raise AssertionError(f"unexpected catalogue header: {(magic, version, scope_limit, record_size, count)}")
    offset = HEADER.size
    rows = []
    for _ in range(count):
        marks = tuple(RECORD.unpack_from(data, offset)[:6])
        fields = RECORD.unpack_from(data, offset)
        rows.append((marks, fields[6], fields[7]))
        offset += record_size
    if offset != len(data):
        raise AssertionError(f"catalogue length mismatch: offset={offset} bytes={len(data)}")
    return scope_limit, rows


def main() -> int:
    results = []
    for scope_limit in (25, 35, 50):
        expected = reference_rows(scope_limit)
        actual_scope, actual = native_rows(ROOT / f"artifacts/dts-rulers-scope{scope_limit}.bin")
        if actual_scope != scope_limit or actual != expected:
            raise AssertionError(f"scope {scope_limit} mismatch: native={len(actual)} reference={len(expected)}")
        results.append({"scope": scope_limit, "valid_rows": len(expected), "mark_sets_and_masks": "exact_match"})
    result = {"status": "passed", "scopes": results, "reference": "independent Python combinations and exact integer masks"}
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
