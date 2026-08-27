#!/usr/bin/env python3
"""Exhaustively screen Wilson's finite-field (211,6,1) difference family."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from verify_dts import verify as verify_primary
from verify_dts_independent import verify as verify_independent


PRIME = 211
FACTORS_OF_PHI = (2, 3, 5, 7)
ROOT = Path(__file__).resolve().parents[1]


def is_primitive_root(value: int) -> bool:
    return all(pow(value, (PRIME - 1) // factor, PRIME) != 1 for factor in FACTORS_OF_PHI)


def coset_indices(generator: int) -> dict[int, int]:
    step = pow(generator, 5, PRIME)
    result: dict[int, int] = {}
    for index in range(5):
        value = pow(generator, index, PRIME)
        for _ in range((PRIME - 1) // 5):
            result[value] = index
            value = value * step % PRIME
    if len(result) != PRIME - 1:
        raise AssertionError("multiplicative cosets did not partition F_211^*")
    return result


def valid_c_values(generator: int) -> list[int]:
    omega = pow(generator, (PRIME - 1) // 3, PRIME)
    omega2 = omega * omega % PRIME
    coset = coset_indices(generator)
    values: list[int] = []
    for c in range(1, PRIME):
        if c in {1, omega, omega2}:
            continue
        probes = (
            (omega - 1) % PRIME,
            c * (omega - 1) % PRIME,
            (c - 1) % PRIME,
            (c - omega) % PRIME,
            (c - omega2) % PRIME,
        )
        if len({coset[value] for value in probes}) == 5:
            values.append(c)
    return values


def wilson_blocks(generator: int, c: int) -> list[list[int]]:
    omega = pow(generator, (PRIME - 1) // 3, PRIME)
    omega2 = omega * omega % PRIME
    step = pow(generator, 5, PRIME)
    base = (1, omega, omega2, c, c * omega % PRIME, c * omega2 % PRIME)
    return [sorted((pow(step, index, PRIME) * value) % PRIME for value in base) for index in range(7)]


def modular_difference_family(blocks: list[list[int]]) -> bool:
    differences = Counter(
        (left - right) % PRIME
        for block in blocks
        for left in block
        for right in block
        if left != right
    )
    return len(differences) == PRIME - 1 and all(differences[value] == 1 for value in range(1, PRIME))


def row_options(block: list[int]) -> list[dict[str, object]]:
    by_row: dict[tuple[int, ...], list[int]] = {}
    for translation in range(PRIME):
        translated = sorted((value + translation) % PRIME for value in block)
        row = tuple(value - translated[0] for value in translated)
        by_row.setdefault(row, []).append(translation)

    options: list[dict[str, object]] = []
    for row, translations in sorted(by_row.items()):
        differences = [row[right] - row[left] for right in range(1, 6) for left in range(right)]
        if len(set(differences)) != 15:
            continue
        mask = sum(1 << difference for difference in differences)
        options.append(
            {
                "row": list(row),
                "mask": mask,
                "translation": translations[0],
                "translation_count": len(translations),
            }
        )
    return options


def pack(options_by_block: list[list[dict[str, object]]], scope_limit: int) -> dict[str, object]:
    order = sorted(range(len(options_by_block)), key=lambda index: len(options_by_block[index]))
    ordered = [options_by_block[index] for index in order]
    best_scope: int | None = None
    best_rows: list[list[int]] | None = None
    best_parameters: list[dict[str, int]] | None = None
    packings = 0
    target_count = 0
    stopped_at_target = False

    def visit(index: int, used: int, rows: list[list[int]], parameters: list[dict[str, int]], current_scope: int) -> None:
        nonlocal best_scope, best_rows, best_parameters, packings, target_count, stopped_at_target
        if stopped_at_target:
            return
        if index == len(ordered):
            packings += 1
            if best_scope is None or current_scope < best_scope:
                best_scope = current_scope
                best_rows = [row[:] for row in rows]
                best_parameters = [item.copy() for item in parameters]
            if current_scope <= scope_limit:
                target_count += 1
                stopped_at_target = True
            return
        if best_scope is not None and current_scope >= best_scope:
            return
        for option in ordered[index]:
            mask = int(option["mask"])
            if used & mask:
                continue
            row = [int(value) for value in option["row"]]
            visit(
                index + 1,
                used | mask,
                rows + [row],
                parameters + [{"block_index": order[index], "translation": int(option["translation"])}],
                max(current_scope, row[-1]),
            )

    visit(0, 0, [], [], 0)
    if best_rows is None:
        return {
            "packings_examined": packings,
            "target_count": target_count,
            "stopped_at_target": stopped_at_target,
            "best_scope": None,
            "best_rows": [],
            "best_parameters": [],
        }
    return {
        "packings_examined": packings,
        "target_count": target_count,
        "stopped_at_target": stopped_at_target,
        "best_scope": best_scope,
        "best_rows": best_rows,
        "best_parameters": best_parameters,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope-limit", type=int, default=111)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()

    primitive_roots = [value for value in range(2, PRIME) if is_primitive_root(value)]
    parameter_pairs: list[dict[str, int]] = []
    families: dict[tuple[tuple[int, ...], ...], tuple[int, int, list[list[int]]]] = {}
    for generator in primitive_roots:
        for c in valid_c_values(generator):
            parameter_pairs.append({"generator": generator, "c": c})
            blocks = wilson_blocks(generator, c)
            if not modular_difference_family(blocks):
                raise AssertionError(f"Wilson construction failed for generator={generator}, c={c}")
            key = tuple(sorted(tuple(block) for block in blocks))
            families.setdefault(key, (generator, c, blocks))

    family_summaries: list[dict[str, object]] = []
    global_best: dict[str, object] | None = None
    for family_index, (generator, c, blocks) in enumerate(families.values()):
        options = [row_options(block) for block in blocks]
        packing = pack(options, args.scope_limit)
        summary = {
            "family_index": family_index,
            "generator": generator,
            "c": c,
            "base_blocks": blocks,
            "row_option_counts": [len(item) for item in options],
            "scope_limit_row_option_counts": [
                sum(int(option["row"][-1]) <= args.scope_limit for option in item) for item in options
            ],
            **packing,
        }
        family_summaries.append(summary)
        if packing["best_scope"] is not None and (
            global_best is None or int(packing["best_scope"]) < int(global_best["best_scope"])
        ):
            global_best = {"family_index": family_index, "generator": generator, "c": c, **packing}
        if bool(packing["stopped_at_target"]):
            break

    best_scope = None if global_best is None else int(global_best["best_scope"])
    best_rows = [] if global_best is None else global_best["best_rows"]
    primary = verify_primary(best_rows) if best_rows else {"valid": False, "scope": None, "errors": ["no complete packing"]}
    independent = verify_independent(best_rows) if best_rows else {"valid": False, "scope": None, "shape_ok": False}
    target_reached = bool(primary["valid"] and independent["valid"] and best_scope is not None and best_scope <= args.scope_limit)
    payload = {
        "construction": "Wilson finite-field (211,6,1) difference family",
        "prime": PRIME,
        "scope_limit": args.scope_limit,
        "primitive_roots_checked": len(primitive_roots),
        "valid_parameter_pairs": parameter_pairs,
        "unique_families_checked": len(family_summaries),
        "family_summaries": family_summaries,
        "best_scope": best_scope,
        "rows": best_rows,
        "best_rows": best_rows,
        "best_parameters": None if global_best is None else {
            "family_index": global_best["family_index"],
            "generator": global_best["generator"],
            "c": global_best["c"],
            "row_translations": global_best["best_parameters"],
        },
        "target_reached": target_reached,
        "target_count": 0 if global_best is None else global_best["target_count"],
        "verification": {"primary": primary, "independent": independent},
        "elapsed_seconds": time.monotonic() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "target_reached": target_reached,
        "primitive_roots_checked": len(primitive_roots),
        "valid_parameter_pairs": len(parameter_pairs),
        "unique_families_checked": len(family_summaries),
        "best_scope": best_scope,
        "best_rows": best_rows,
        "verification": {"primary_valid": primary["valid"], "independent_valid": independent["valid"]},
        "elapsed_seconds": payload["elapsed_seconds"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
