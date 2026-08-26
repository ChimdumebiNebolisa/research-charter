# Research Charter

This repository is the locked foundation for a controlled research tournament over exactly three fixed open problems. It is in Foundation Phase only. No novel search, optimization, or large experiment has been run here, and Phase 2 is not authorized by this repository.

| Problem | Frozen baseline | Strict-improvement target |
| --- | --- | --- |
| `dts_7_5` | Published valid `(7,5)` DTS with scope `112` | Valid scope `<=111` |
| `heilbronn_n12` | Comellas–Yebra 12-point unit-square construction, `H12 >= 0.032599...` | A rigorously checked configuration with minimum area strictly above that exact baseline |
| `kserver_k4_circle` | `3` violations on the pinned `circle_taxi_k4_m6.pickle` evaluator instance | Fewer than `3` violations under the identical pinned contract |

The Heilbronn value is a credible published construction baseline, not a proof of global optimality. The k-server finite evaluator is sound for refuting a candidate but incomplete as a proof of the full conjecture. These distinctions are part of the frozen problem definitions.

## Repository map

- `governance/` contains the constitutional rules and verification policy.
- `problems/` contains the frozen definitions, baselines, and problem-specific verification contracts.
- `schemas/` defines the shape of experiment, candidate, and decision records.
- `experiments/` is reserved for append-oriented research evidence; it is intentionally empty in Foundation Phase.
- `state/` contains derived summaries and append-only research memory.
- `scripts/` contains repository integrity, drift, and schema checks.
- `upstreams.lock.json` records the exact external sources and code revisions used for the foundation.

Useful checks from the repository root:

```text
python scripts/validate_experiment.py --path experiments
python scripts/validate_candidate.py --path experiments
python scripts/check_drift.py --path experiments
python scripts/check_foundation_lock.py
python -m unittest discover -s tests -v
```

The final command assumes the `foundation-v1` tag has been created. Repository-local checks are safeguards, not an absolute security boundary: a user or automation with unrestricted GitHub administration can bypass local policy by rewriting history, deleting tags, or changing branch protection.

## Foundation status

The foundation is considered ready for Phase 2 only after a human reviews the commit, pushes the commit and `foundation-v1` tag, enables the GitHub settings in `governance/GITHUB_PROTECTION_SETUP.md`, and explicitly supplies the Phase 2 instruction.
