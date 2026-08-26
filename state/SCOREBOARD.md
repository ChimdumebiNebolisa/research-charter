# Scoreboard

This is a derived summary, not the source of scientific truth. It is intentionally empty of experiment results in Foundation Phase.

| Problem | Frozen baseline | Target | Foundation status |
| --- | --- | --- | --- |
| `dts_7_5` | scope `112` | scope `<=111` | baseline independently verified; no improving candidate; search PAUSED |
| `heilbronn_n12` | source-faithful `0.032598858691819698...` | certified minimum area strictly greater | search BLOCKED: protected Markdown transcription yields zero area |
| `kserver_k4_circle` | reported `3` violations on pinned `circle_taxi_k4_m6.pickle` | fewer than `3` | search BLOCKED: native Windows evaluator multiprocessing failure |

## Phase 2 evidence after ten substantive experiments

- DTS local perturbation: scope `111`, but only `100/105` unique differences; duplicate set `[13, 36, 53, 100, 111]` across all three seeds (Level 1 proxy signal).
- DTS from-scratch random greedy: at most `4` mutually disjoint rows / `60` unique differences across three seeds (Level 1 proxy signal).
- DTS radius-10 first-row exhaustive replacement: no compatible complete row against six fixed rows (Level 1 localized negative evidence).
- DTS coordinated conflict repair: no improvement beyond `100/105` unique differences (Level 1 proxy signal).
- DTS first pool-backtracking implementation: row-0 pool saturated at `114–133` candidates and starved DFS (Level 1 implementation failure, not a mathematical negative).
- DTS bounded pool-backtracking correction: no disjoint pair among tiny sampled pools; best DFS depth `1` (Level 1 proxy/negative search signal).
- DTS CP-SAT: native OR-Tools crashed before status, including a three-variable control model (runtime blocker; no feasibility inference).
- DTS upstream-inspired block deletion: all three seeds reached five rows/75 unique differences with no full trial; this is partial proxy movement only.
- No true-objective movement has been verified.
- Current allocation: all active research paused; no hedge; Heilbronn `BLOCKED_FOUNDATION_INTEGRITY`, k-server `BLOCKED_RUNTIME`, DTS paused pending a new runtime or representation.
