#!/usr/bin/env python3
"""Independent integer verifier for normalized difference triangle sets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def verify(rows: list[list[int]]) -> dict[str, object]:
    errors: list[str] = []
    if len(rows) != 7:
        errors.append(f"expected 7 rows, got {len(rows)}")
    for row_index, row in enumerate(rows):
        if len(row) != 6:
            errors.append(f"row {row_index}: expected 6 entries, got {len(row)}")
            continue
        if any(not isinstance(value, int) or isinstance(value, bool) for value in row):
            errors.append(f"row {row_index}: entries must be integers")
        if row[0] != 0:
            errors.append(f"row {row_index}: first entry is not zero")
        if any(value < 0 for value in row):
            errors.append(f"row {row_index}: negative entry")
        if any(left >= right for left, right in zip(row, row[1:])):
            errors.append(f"row {row_index}: entries are not strictly increasing")

    differences: dict[int, list[list[int]]] = {}
    for row_index, row in enumerate(rows):
        if len(row) != 6:
            continue
        for right in range(1, 6):
            for left in range(right):
                difference = row[right] - row[left]
                differences.setdefault(difference, []).append([row_index, left, right])

    duplicate_set = sorted(difference for difference, occurrences in differences.items() if len(occurrences) > 1)
    if duplicate_set:
        errors.append(f"duplicate positive differences: {duplicate_set}")

    scope = max((row[-1] for row in rows if len(row) == 6), default=None)
    return {
        "valid": not errors and len(differences) == 105,
        "errors": errors,
        "row_count": len(rows),
        "difference_count": sum(len(occurrences) for occurrences in differences.values()),
        "unique_difference_count": len(differences),
        "duplicate_set": duplicate_set,
        "scope": scope,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))
    result = verify(payload["rows"] if isinstance(payload, dict) else payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
