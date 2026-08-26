# Frozen k-server Baseline

Status: `RESOLVED_REPORTED_PRIMARY_EVALUATOR_RESULT`.

```text
problem_id: kserver_k4_circle
metric: violations_k
primary_metric_file: circle_taxi_k4_m6.pickle
inequalities_checked: 7000602
reported_best: 3
target: violations_k < 3
```

The pinned upstream README reports a human-designed 17-violation potential and a candidate with 3 violations out of approximately 7 million inequalities. The pinned task hint gives the exact `circle_taxi_k4_m6.pickle` count as `7,000,602` inequalities. The 2026 benchmark paper independently reports the 3-violation result for the `(k=4,m=6)` augmented instance.

The 3 count is therefore frozen as the current reported primary-evaluator baseline. This foundation does not run the multi-million-edge evaluator and does not claim an independent local reproduction of the candidate coefficient vector, because that vector is not included in the pinned public revision. That provenance limitation must remain visible in any future scoreboard.

Primary references: [arXiv:2604.07240](https://arxiv.org/abs/2604.07240), §3.2; [pinned README](https://github.com/kibrq/k-server-bench/blob/aea64346b846c967e4448f098d4b8b1748504d27/README.md); [pinned k4 metric hint](https://github.com/kibrq/k-server-bench/blob/aea64346b846c967e4448f098d4b8b1748504d27/tasks/hints/metrics/k4_general_task/README.md).
