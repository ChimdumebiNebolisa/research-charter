# Research Charter

Status: frozen at Foundation Phase. This document is constitutional. Autonomous sessions may not amend it.

## Scope

This repository hosts a controlled tournament over exactly these three research questions:

1. `dts_7_5`: find a valid minimum-scope `(7,5)` Difference Triangle Set.
2. `heilbronn_n12`: find a rigorously defensible 12-point configuration in the unit square that strictly improves the frozen credible minimum-triangle-area baseline.
3. `kserver_k4_circle`: discover a potential for the public `k=4` circle/circle-taxi k-server formulation that has fewer violations than the frozen record under the identical evaluator contract.

The immutable machine-readable registry is `problems/PROBLEM_REGISTRY.json`. Those are the only allowed questions.

## Allowed autonomous activity after explicit Phase 2 authorization

An agent may invent algorithms, representations, search strategies, experimental code, and combinations of methods. It may use SAT, SMT, CP-SAT, MILP, local search, evolutionary methods, symbolic methods, or other appropriate techniques. It may stop failed directions and allocate work unevenly among the three problems.

## Prohibitions

An agent may not:

- introduce a fourth research problem or broaden/substitute a listed problem;
- weaken a target, redefine a success metric, or modify a baseline because it is inconvenient;
- treat proxy improvement, evaluator acceptance, or finite empirical evidence as a proof or final research result;
- alter validation or frozen upstream code to make a candidate pass;
- optimize a benchmark loophole instead of the intended mathematical object;
- claim novelty without a provenance and prior-art check;
- delete, hide, rewrite, or selectively omit failures and negative results;
- repeatedly run essentially identical experiments without a written justification;
- turn infrastructure polishing into the research objective;
- change a protected file without explicit human authorization;
- declare the full k-server conjecture solved from finite zero-violation data.

## Change control

Any proposed change to the research questions, objective, baseline, target, benchmark, or validation contract must be documented in `governance/AMENDMENTS.md`, explicitly authorized by a human owner, and released as a new foundation version. Autonomous agents cannot authorize amendments themselves.

## Phase boundary

Foundation Phase establishes sources, definitions, targets, schemas, and controls. It does not search for solutions or run research experiments. Phase 2 begins only after human review of the foundation commit and an explicit Phase 2 instruction.
