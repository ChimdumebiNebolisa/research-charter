# Verification Policy

Verification is conceptually separate from candidate search. Search code may propose objects; frozen verification decides whether those objects satisfy the contract.

## Rules

- Use the exact upstream revision and metric inputs recorded in `upstreams.lock.json`.
- Do not modify, replace, monkey-patch, or vendor a different final validator during ordinary research.
- Rerun an apparent improvement from a clean checkout with the recorded dependency and evaluator revisions.
- Prefer deterministic or independently reproducible checks over an LLM judge whenever deterministic checking is possible.
- State known evaluator limitations next to every result.
- Verify floating-point record claims using higher precision, interval arithmetic, exact arithmetic, or another appropriate certification method.
- Treat a benchmark loophole as a finding about the evaluator, not automatically as a solution to the mathematical problem.
- Preserve failed validation outputs and the reason for rejection.

## Problem-specific requirements

- DTS validation must check row normalization, strict order, global uniqueness of every positive within-row difference, and scope using integer arithmetic.
- Heilbronn validation must check all 220 triangle determinants for 12 points and keep the strict improvement comparison exact or certified. A float64 improvement alone cannot produce a record claim.
- k-server validation must use the pinned evaluator and metric files. A violated inequality refutes that candidate for that checked instance; satisfying every finite checked inequality is not a proof of the full conjecture.

No validation result may override the frozen mathematical intent documented in `problems/*/PROBLEM.md`.
