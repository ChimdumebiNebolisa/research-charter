"""Minimal Windows compatibility surface for the upstream evaluator import.

The pinned evaluator imports POSIX ``resource`` even when its candidate
subprocess path is bypassed with ``--potential_kwargs_json``.  These no-op
limits are used only for that Windows-compatible execution path; the upstream
evaluator and metric files remain untouched.
"""

RLIMIT_AS = 9
RLIMIT_CPU = 0


def setrlimit(_kind: int, _limits: tuple[int, int]) -> None:
    return None
