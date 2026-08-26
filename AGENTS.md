# Operating Rules for Autonomous Research Sessions

This file is protected by `governance/PROTECTED_FILES.md`. It applies to every Codex or other autonomous session operating in this repository.

## Current phase

This repository is Foundation Phase only until a human explicitly authorizes Phase 2. Do not search for novel solutions, optimize candidates, run large experiments, or claim research progress during Foundation Phase. The foundation task is setup and verification only.

## Constitutional scope

The only allowed research questions are the three entries in `problems/PROBLEM_REGISTRY.json`:

- `dts_7_5`
- `heilbronn_n12`
- `kserver_k4_circle`

Do not add a fourth problem, substitute a neighboring problem, change an objective, change a target, weaken a metric, or alter a validation contract. A proposed change must be a human-authorized amendment recorded in `governance/AMENDMENTS.md`; an autonomous session cannot authorize one.

## Protected foundation

Before any work, read the relevant governance and problem files. Do not modify protected files during ordinary research. Do not modify or replace a frozen evaluator, baseline, upstream lock, schema, integrity workflow, or integrity checker to make a candidate pass. If a protected file is genuinely wrong, stop and request an explicit human amendment and a new foundation version.

The `foundation-v1` tag is the integrity reference. Use branches for all work. Do not force-push, delete tags, rewrite experiment history, or delete failed records.

## Evidence discipline

Every experiment and candidate must use the schemas under `schemas/`. Every experiment must identify exactly one frozen `problem_id` and matching `target_id`, record its hypothesis, rationale, information gain, method, objective relation, configuration, seeds, resource budget, kill condition, artifacts, raw result, comparison, evidence level, interpretation, failure mode, lesson, and next action.

Experiments are append-oriented historical evidence. Failed, inconclusive, and rejected work remains visible. Consult `state/LESSONS.jsonl` before proposing a new experiment. Repeating an essentially identical experiment requires a written justification and a reason it can produce new information.

Do not call proxy movement a true-objective improvement. Do not call a public evaluator pass a proof. Do not call a floating-point result a certified Heilbronn record. Do not call zero finite k-server violations a proof of the full conjecture. Novelty requires a prior-art/provenance review.

## Verification and safety

Use the frozen primary evaluator and independent verification procedures defined for the problem. Research code may be changed on a branch, but final verification logic and protected benchmark definitions may not be changed during ordinary research. Keep exact or certified arithmetic where the problem requires it. Do not add credentials, secrets, or network-dependent hidden behavior to candidates.

Before reporting progress, run the repository checks, record the exact commit SHA, preserve artifacts, and state uncertainty and limitations. If a baseline is marked `BASELINE_UNRESOLVED`, research on that problem is blocked until a human resolves it.
