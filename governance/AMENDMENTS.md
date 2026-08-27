# Amendments

## AMEND-2026-08-27-heilbronn-baseline-transcription-v2

- **Date:** 2026-08-27
- **Authorization:** The human repository owner explicitly authorized this amendment in the 2026-08-27 task prompt. This entry records that authorization; it is not autonomous approval.
- **Protected files changed:** `problems/heilbronn_n12/BASELINE.md`, `governance/AMENDMENTS.md`, `governance/PROTECTED_FILES.md`, `governance/GITHUB_PROTECTION_SETUP.md`, `README.md`, and `scripts/check_foundation_lock.py`.
- **Exact correction:** Replace the first Comellas–Yebra coordinate `(0,0)` with `(x,0)`, where `x = 1 - ((27 + 3*sqrt(57))^(2/3) + 6)/(6*(27 + 3*sqrt(57))^(1/3))`. The remaining eleven coordinates, `y = 2*x^2 - 3*x + 1/2`, the exact baseline `B_H12 = x/4 + x*y/2 - x^2/2`, and the strict-improvement target are unchanged.
- **Reason:** The protected Markdown transcription disagreed with the primary source and made points 0, 2, and 8 collinear, producing a zero-area triangle. The source-faithful page-7 coordinate table uses `(x,0)`.
- **Primary evidence:** [Comellas and Yebra (2002), primary PDF, page 7](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v9i1r6/pdf/). Local evidence is preserved in `experiments/heilbronn_n12/baseline-reproduction-001.json`, `experiments/heilbronn_n12/raw/frozen_transcription_verification.json.txt`, `experiments/heilbronn_n12/raw/source_faithful_coordinates.json.txt`, and `artifacts/baselines/heilbronn_comellas_yebra.json`.
- **Independent re-verification:** The exact verifier enumerates all 220 triangles of the corrected configuration, finds them positive, and obtains minimum area `0.032598858691819698218764006623515408049241988379776913777741905474205601650786197`, exactly equal to the algebraic baseline. The old transcription has zero triangle `[0,2,8]`.
- **Comparability and limits:** This is a source-faithful transcription correction, not a new construction or objective change. The baseline remains a credible published lower-bound construction, not a proof of Heilbronn optimality; historical records that reported the protected inconsistency remain historically true.
- **Migration and release:** Re-run the exact Heilbronn verifier and full repository integrity suite, then release the clean constitutional commit as the annotated `foundation-v2` tag. Preserve `foundation-v1` unchanged and retain `--tag foundation-v1` for explicit historical comparison.

An amendment proposal must include:

1. the exact protected file and proposed change;
2. the reason the foundation is inadequate;
3. the effect on comparability with existing evidence;
4. a migration and re-verification plan;
5. explicit human authorization;
6. a new foundation commit and version tag.

Autonomous agents may record an explicitly authorized amendment here, but may not authorize one.
