# `k=4` Circle k-server Potential Discovery

## Frozen question

Use the public `k-server-bench` formulation to search for a potential function for four servers on the circle and its circle-taxi augmentation. The benchmark represents work functions on precomputed metric instances and checks inequalities of the form

```text
Phi(v) - Phi(u) >= max_X(w_v(X)-w_u(X))
                         - (c+1)*(min_X w_v(X)-min_X w_u(X))
```

at competitiveness `c=k=4`. The primary frozen comparison is the `circle_taxi_k4_m6.pickle` instance and its `violations_k` count.

The true scientific objective is a mathematically valid potential for the k-server conjecture formulation, not merely an object that exploits a finite dataset, a parser, a timeout, or a numerical tolerance. The frozen tournament target is fewer than three violations under the identical pinned evaluator and metric contract.

## Objective versus evaluator

The upstream evaluator owns candidate loading, metric data, potential instantiation, and scoring. Candidate code proposes a potential or its parameters; it may not redefine `violations_k`, alter metric files, skip inequalities, or replace the evaluator. The public general-task metric suite contains `circle_k4_m6`, `circle_k4_m8`, `circle_taxi_k4_m6`, and `circle_taxi_k4_m8`; the three-violation record is specifically reported for the `m=6` circle-taxi instance.

The evaluator is sound but incomplete: a violated inequality refutes the candidate for that checked transition, while zero violations on a finite precomputed instance do not prove the full k-server conjecture.

## Evidence boundaries

A lower violation count on the primary pinned instance is Level 2 until independently reproduced. A clean reproduction and adversarial checks are required before a research claim. Zero finite violations must never be described as solving the conjecture.

## Primary sources and provenance

- [Brilliantov, Bamas, and Abbé, *k-server-bench: Automating Potential Discovery for the k-Server Conjecture*](https://arxiv.org/abs/2604.07240), 2026, especially the open `k=4` discussion. It reports the best candidate with 3 violations out of roughly 7 million checked inequalities.
- [Pinned upstream repository](https://github.com/kibrq/k-server-bench), commit `aea64346b846c967e4448f098d4b8b1748504d27`. The README reports the 17-violation human baseline and the 3-violation candidate; `docs/concepts.md`, `tasks/hints/metrics/k4_general_task/README.md`, and `tools/evaluator/evaluate.py` define the benchmark-facing contract.
