# Evidence Standard

Evidence levels are monotone claims about what has actually been shown. A record must never use terminology from a higher level than it has earned.

## Levels

### Level 0 — Idea

An unexecuted hypothesis or proposed method. No measurement exists.

### Level 1 — Experimental signal

A measured result on a proxy, subset, heuristic evaluator, or exploratory run. It may guide work but does not establish progress on the frozen objective.

### Level 2 — Primary-evaluator result

A candidate improves the frozen public or primary metric under the pinned evaluator and records the exact inputs, code revision, and raw output.

### Level 3 — Independent reproduction

The result reproduces from a clean checkout with fixed dependencies and deterministic or adequately repeated evaluation by an independent run or verifier.

### Level 4 — Adversarial verification

The result survives independent checks designed to detect evaluator exploitation, numerical artifacts, leakage, hard-coding, incomplete generalization, or other false progress.

### Level 5 — Research claim

The evidence supports a carefully scoped scientific or mathematical claim after prior-art review and, where applicable, rigorous proof or certification.

## Required language

- `promising` is not `improved`;
- `public evaluator passed` is not `proved`;
- `numerically better` is not `new record`;
- `zero finite violations` is not `solved conjecture`;
- `novel to this agent` is not `novel to the literature`.

The experiment and candidate schemas require an explicit evidence level and limitations. A lower-level result may be valuable, but it must remain labeled as such.
