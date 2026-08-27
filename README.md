# Research Charter

This repository is the locked foundation and append-oriented research record for a controlled tournament over exactly three fixed open problems. Phase 2 is authorized by the human repository owner; the recorded research history contains failed, inconclusive, and negative results, and no novel frozen-target contribution has been verified.

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
- `experiments/` contains append-oriented research evidence, including failed and inconclusive records.
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

The final command checks the active `foundation-v2` tag. The immutable `foundation-v1` tag remains available for historical comparison. Repository-local checks are safeguards, not an absolute security boundary: a user or automation with unrestricted GitHub administration can bypass local policy by rewriting history, deleting tags, or changing branch protection.

## Foundation status

The active foundation is `foundation-v2`, released after the human-authorized Heilbronn transcription amendment. `foundation-v1` remains immutable historical evidence. GitHub settings are described in `governance/GITHUB_PROTECTION_SETUP.md` and must be verified separately from this file.
