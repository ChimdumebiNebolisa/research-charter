"""Run the pinned n=7 search with one heavy worker per stage.

The pinned upstream controller unconditionally creates two stage-C workers and
one stage-D worker. This wrapper executes the pinned source in an isolated
namespace with only the duplicate stage-C spawn removed, then narrows the
existing worker-budget constants. Search logic, candidate scoring, and the
evaluator remain the pinned implementations.
"""

from __future__ import annotations

import multiprocessing as mp
from pathlib import Path
import sys
import types


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: run_kserver_n7_single_heavy.py SEARCH_SCRIPT [ARGS ...]")

    search_script = sys.argv[1]
    search_args = sys.argv[2:]
    source = Path(search_script).read_text(encoding="utf-8")
    duplicate_spawn = '    spawn_heavy_worker("stage_c", "stage_c_1", STAGE_C_MAX_CPUS)\n'
    if source.count(duplicate_spawn) != 1:
        raise RuntimeError("pinned search source did not contain the expected duplicate stage-C spawn")
    source = source.replace(duplicate_spawn, "", 1)

    mp.set_start_method("fork")
    search_module = types.ModuleType("n7_search_module")
    search_module.__file__ = search_script
    search_module.__package__ = None
    sys.modules[search_module.__name__] = search_module
    execution_globals = search_module.__dict__
    exec(compile(source, search_script, "exec"), execution_globals)

    execution_globals["FAST_WORKERS_TOTAL"] = 1
    execution_globals["FAST_STAGE_A_WORKERS"] = 1
    execution_globals["FAST_STAGE_B_WORKERS"] = 1
    execution_globals["HEAVY_CPU_BUDGET"] = 1
    execution_globals["STAGE_C_MAX_CPUS"] = 1
    execution_globals["STAGE_D_MIN_CPUS"] = 1
    execution_globals["STAGE_C_BATCH_SIZE"] = 1
    execution_globals["STAGE_D_BATCH_SIZE"] = 1

    sys.argv = [search_script, *search_args]
    execution_globals["main"]()


if __name__ == "__main__":
    main()
