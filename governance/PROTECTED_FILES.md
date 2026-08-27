# Protected Foundation Files

The files below are the integrity boundary for ordinary research branches. The active foundation reference is the `foundation-v2` tag; `foundation-v1` remains the immutable historical comparison reference. A change to any listed path requires explicit human intervention and a new foundation version.

The repository-local check is not tamper-proof against an actor who can rewrite Git history, delete tags, modify workflows, or administer the GitHub repository. GitHub branch protection and human review are therefore required operational controls, not optional decoration.

The following block is machine-readable by `scripts/check_foundation_lock.py`:

<!-- protected-files:start -->
- `README.md`
- `AGENTS.md`
- `governance/RESEARCH_CHARTER.md`
- `governance/PROTECTED_FILES.md`
- `governance/EVIDENCE_STANDARD.md`
- `governance/VERIFICATION_POLICY.md`
- `governance/DECISION_POLICY.md`
- `governance/DRIFT_POLICY.md`
- `governance/AMENDMENTS.md`
- `governance/GITHUB_PROTECTION_SETUP.md`
- `problems/PROBLEM_REGISTRY.json`
- `problems/dts_7_5/PROBLEM.md`
- `problems/dts_7_5/BASELINE.md`
- `problems/dts_7_5/VERIFICATION.md`
- `problems/heilbronn_n12/PROBLEM.md`
- `problems/heilbronn_n12/BASELINE.md`
- `problems/heilbronn_n12/VERIFICATION.md`
- `problems/kserver_k4_circle/PROBLEM.md`
- `problems/kserver_k4_circle/BASELINE.md`
- `problems/kserver_k4_circle/VERIFICATION.md`
- `schemas/experiment.schema.json`
- `schemas/candidate.schema.json`
- `schemas/decision.schema.json`
- `scripts/validate_experiment.py`
- `scripts/validate_candidate.py`
- `scripts/check_drift.py`
- `scripts/check_foundation_lock.py`
- `scripts/validate_decision.py`
- `.github/CODEOWNERS`
- `.github/workflows/research-integrity.yml`
- `upstreams.lock.json`
<!-- protected-files:end -->

State files, experiment records, candidate artifacts, and derived scoreboard data are intentionally mutable or append-oriented and are not part of this frozen-file comparison. They remain subject to schema and drift checks.
