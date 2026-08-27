#!/usr/bin/env python3
"""Second DTS check using a flat list and a frequency counter."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def verify(rows: list[list[int]]) -> dict[str, object]:
    differences = [
        row[j] - row[i]
        for row in rows
        for i in range(6)
        for j in range(i + 1, 6)
    ] if all(len(row) == 6 for row in rows) else []
    frequencies = Counter(differences)
    duplicates = sorted(value for value, count in frequencies.items() if count != 1)
    shape_ok = len(rows) == 7 and all(
        len(row) == 6
        and row[0] == 0
        and all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in row)
        and all(row[i] < row[i + 1] for i in range(5))
        for row in rows
    )
    return {
        "valid": shape_ok and len(differences) == 105 and len(frequencies) == 105,
        "shape_ok": shape_ok,
        "difference_count": len(differences),
        "unique_difference_count": len(frequencies),
        "duplicates": duplicates,
        "scope": max((row[5] for row in rows), default=None),
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
