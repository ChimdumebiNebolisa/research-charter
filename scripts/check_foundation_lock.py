#!/usr/bin/env python3
"""Ensure protected foundation files equal their foundation tag contents."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "governance" / "PROTECTED_FILES.md"
START = "<!-- protected-files:start -->"
END = "<!-- protected-files:end -->"


def protected_files() -> list[str]:
    text = MANIFEST.read_text(encoding="utf-8")
    try:
        block = text.split(START, 1)[1].split(END, 1)[0]
    except IndexError as exc:
        raise ValueError("protected-file manifest markers are missing") from exc
    paths = re.findall(r"^- `([^`]+)`$", block, flags=re.MULTILINE)
    if not paths:
        raise ValueError("protected-file manifest is empty")
    if len(paths) != len(set(paths)):
        raise ValueError("protected-file manifest contains duplicates")
    return paths


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def validate(tag: str, allow_uninitialized: bool = False) -> list[str]:
    paths = protected_files()
    if git("rev-parse", "--is-inside-work-tree", check=False).returncode != 0:
        return ["not inside a Git worktree"]
    tag_ref = git("rev-parse", "--verify", f"{tag}^{{commit}}", check=False)
    if tag_ref.returncode != 0:
        if allow_uninitialized:
            return ["foundation tag is not present; protected-file existence checks were not compared"]
        return [f"foundation tag {tag!r} is missing; create it only after the clean foundation commit"]
    errors: list[str] = []
    for path in paths:
        current = ROOT / path
        if not current.is_file():
            errors.append(f"protected file missing from worktree: {path}")
            continue
        if git("cat-file", "-e", f"{tag}:{path}", check=False).returncode != 0:
            errors.append(f"protected file missing from {tag}: {path}")
            continue
        if git("diff", "--quiet", tag, "--", path, check=False).returncode != 0:
            errors.append(f"protected file differs from {tag}: {path}")
        if git("status", "--porcelain", "--", path, check=False).stdout:
            errors.append(f"protected file has uncommitted or untracked changes: {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="foundation-v1")
    parser.add_argument("--allow-uninitialized", action="store_true")
    args = parser.parse_args()
    try:
        errors = validate(args.tag, args.allow_uninitialized)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 0 if args.allow_uninitialized and len(errors) == 1 and errors[0].startswith("foundation tag") else 1
    print(f"foundation lock passed: {args.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
