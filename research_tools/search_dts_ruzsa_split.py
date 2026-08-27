#!/usr/bin/env python3
"""Exhaustively test the Ruzsa modular-ruler split construction for (7,5)."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np

from verify_dts import verify


def primitive_roots(prime: int) -> list[int]:
    roots: list[int] = []
    required = {pow(prime, 1, prime)}
    phi = prime - 1
    factors = [factor for factor in range(2, phi + 1) if phi % factor == 0]
    for candidate in range(2, prime):
        if len({pow(candidate, exponent, prime) for exponent in range(1, prime)}) != phi:
            continue
        if all(pow(candidate, phi // factor, prime) != 1 for factor in factors if factor != phi):
            roots.append(candidate)
    return roots


def ruzsa_ruler(prime: int, generator: int) -> tuple[int, list[int]]:
    modulus = prime * (prime - 1)
    values = sorted(
        {
            (prime * index + (prime - 1) * pow(generator, index, prime)) % modulus
            for index in range(1, prime)
        }
    )
    return modulus, values


def modular_valid(values: list[int], modulus: int) -> bool:
    differences = [
        (right - left) % modulus
        for left in values
        for right in values
        if left != right
    ]
    return len(differences) == len(set(differences)) == len(values) * (len(values) - 1)


def split_rows(values: list[int], modulus: int, multiplier: int, translation: int) -> list[list[int]] | None:
    transformed = [(multiplier * value + translation) % modulus for value in values]
    classes: list[list[int]] = [[] for _ in range(7)]
    for value in transformed:
        classes[value % 7].append(value)
    if any(len(group) != 6 for group in classes):
        return None
    return [[(value - min(group)) // 7 for value in sorted(group)] for group in classes]


def run(prime: int, limit: int) -> dict[str, object]:
    started = time.monotonic()
    best_scope: int | None = None
    best_rows: list[list[int]] = []
    best_parameters: dict[str, int] = {}
    checked_transforms = 0
    modular_checks = 0
    target_rows: list[list[list[int]]] = []
    target_count = 0
    invalid_target_count = 0
    generators = primitive_roots(prime)
    for generator in generators:
        modulus, base = ruzsa_ruler(prime, generator)
        modular_checks += 1
        if not modular_valid(base, modulus):
            continue
        for multiplier in range(1, modulus):
            if math.gcd(multiplier, modulus) != 1:
                continue
            transformed = np.array([(multiplier * value) % modulus for value in base], dtype=np.int64)
            shifted = (transformed[None, :] + np.arange(modulus, dtype=np.int64)[:, None]) % modulus
            groups = [[index for index, value in enumerate(transformed) if int(value) % 7 == residue] for residue in range(7)]
            spans = np.stack(
                [shifted[:, indices].max(axis=1) - shifted[:, indices].min(axis=1) for indices in groups],
                axis=1,
            )
            scopes = spans.max(axis=1) // 7
            checked_transforms += modulus
            minimum_translation = int(np.argmin(scopes))
            minimum_scope = int(scopes[minimum_translation])
            if best_scope is None or minimum_scope < best_scope:
                candidate = split_rows(base, modulus, multiplier, minimum_translation)
                checked = verify(candidate) if candidate is not None else {"valid": False, "scope": None}
                if checked["valid"]:
                    best_scope = minimum_scope
                    best_rows = candidate or []
                    best_parameters = {
                        "generator": generator,
                        "multiplier": multiplier,
                        "translation": minimum_translation,
                    }
            qualifying = np.flatnonzero(scopes <= limit)
            target_count += int(len(qualifying))
            for translation in qualifying[:3]:
                translation_int = int(translation)
                rows = split_rows(base, modulus, multiplier, translation_int)
                if rows is None:
                    invalid_target_count += 1
                    continue
                checked = verify(rows)
                if not checked["valid"]:
                    invalid_target_count += 1
                elif len(target_rows) < 3:
                    target_rows.append(rows)
    return {
        "method": "ruzsa-modular-ruler-residue-class-split",
        "prime": prime,
        "modulus": prime * (prime - 1),
        "limit": limit,
        "generators": generators,
        "modular_rulers_checked": modular_checks,
        "transforms_with_balanced_residue_classes": checked_transforms,
        "best_scope": best_scope,
        "best_rows": best_rows,
        "best_parameters": best_parameters,
        "target_count": target_count,
        "invalid_target_count": invalid_target_count,
        "target_rows": target_rows[:3],
        "verification": verify(best_rows) if best_rows else {"valid": False, "scope": None},
        "elapsed_seconds": time.monotonic() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prime", type=int, default=43)
    parser.add_argument("--limit", type=int, default=111)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.prime, args.limit)
    payload["target_reached"] = bool(payload["target_count"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "target_reached": payload["target_reached"],
                "best_scope": payload["best_scope"],
                "transforms": payload["transforms_with_balanced_residue_classes"],
                "output": str(args.output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
