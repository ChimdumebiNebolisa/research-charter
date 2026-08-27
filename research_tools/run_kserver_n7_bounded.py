"""Run the pinned n=7 search with a local-memory-safe worker budget.

The upstream script is loaded without executing its ``__main__`` block, then
its existing worker-budget constants are narrowed before calling its existing
``main`` function. No evaluator, metric, or search-stage implementation is
replaced by this wrapper.
"""

from __future__ import annotations

import multiprocessing as mp
import runpy
import sys


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: run_kserver_n7_bounded.py SEARCH_SCRIPT [ARGS ...]")

    search_script = sys.argv[1]
    search_args = sys.argv[2:]
    mp.set_start_method("fork")
    module = runpy.run_path(search_script, run_name="n7_search_module")

    # The default documented configuration exhausted the 7.6 GiB WSL instance
    # during worker initialization. Keep the same search, but bound aggregate
    # resident memory to make a useful local execution possible.
    # runpy returns a namespace copy on this Python version; functions retain
    # the execution namespace in __globals__, so patch that namespace.
    search_globals = module["main"].__globals__
    search_globals["FAST_WORKERS_TOTAL"] = 1
    search_globals["FAST_STAGE_A_WORKERS"] = 1
    search_globals["FAST_STAGE_B_WORKERS"] = 1
    search_globals["HEAVY_CPU_BUDGET"] = 2
    search_globals["STAGE_C_MAX_CPUS"] = 1
    search_globals["STAGE_D_MIN_CPUS"] = 1
    search_globals["STAGE_C_BATCH_SIZE"] = 1
    search_globals["STAGE_D_BATCH_SIZE"] = 1

    sys.argv = [search_script, *search_args]
    module["main"]()


if __name__ == "__main__":
    main()
