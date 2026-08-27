#!/usr/bin/env python3
"""Run the pinned evaluator with fork semantics for Python 3.14 compatibility."""

from __future__ import annotations

import multiprocessing as mp
import runpy
import sys


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: run_kserver_evaluator_fork.py /path/to/evaluate.py [args ...]")
    mp.set_start_method("fork")
    sys.argv = sys.argv[1:]
    runpy.run_path(sys.argv[0], run_name="__main__")
