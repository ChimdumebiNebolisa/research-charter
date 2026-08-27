# Scoreboard

This is a derived summary, not the source of scientific truth. It is intentionally empty of experiment results in Foundation Phase.

| Problem | Frozen baseline | Target | Foundation status |
| --- | --- | --- | --- |
| `dts_7_5` | scope `112` | scope `<=111` | baseline independently verified; no improving candidate; direct solvers/local/global exact-cover searches unresolved; search PAUSED |
| `heilbronn_n12` | source-faithful `0.032598858691819698...` | certified minimum area strictly greater | search BLOCKED: protected Markdown transcription yields zero area |
| `kserver_k4_circle` | reported `3` violations on pinned `circle_taxi_k4_m6.pickle` | fewer than `3` | evaluator operational in WSL; available parametrized baseline scores `17`; reported 3-vector/search workspace absent |

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
- k-server fork-compatible primary evaluator: exact pinned parametrized example scores `17` violations, matching the upstream human-designed baseline (Level 2 primary-evaluator measurement); the reported 3-violation candidate is not present in the pinned checkout.
- DTS Linux CP-SAT capability probe: unchanged scope-111 model returns `UNKNOWN` after `120.147` seconds under WSL2 OR-Tools `9.15.6755`, with no candidate or bound (Level 1 solver evidence).
- DTS Z3 direct model: `unknown` after `120.017` seconds, with no candidate or bound (Level 1 solver evidence).
- DTS coordinated radius-3 neighborhood: 48,100 valid row masks; Python exact-cover DFS reached depth 5 before 5,000,000 nodes, candidate-level CP-SAT returned `UNKNOWN`, and Glucose4 timed out (Level 1 finite-family evidence only).
- DTS global uniform catalog: 250,000 valid row masks; rare-difference branching reached depth 4 before 2,000,000 nodes (Level 1 finite sampled-family evidence only).
- Heilbronn source-faithful SLSQP: 12 starts returned to the published minimum within float64 noise; no certification or improvement claim.
- No true-objective movement has been verified.
- Current allocation: `WAITING_FOR_CAPABILITY`; no primary or hedge. Heilbronn `BLOCKED_FOUNDATION_INTEGRITY`; DTS requires a structural decomposition; k-server evaluator is operational but candidate provenance/search workspace is missing.

## Phase 2 evidence after twenty-four substantive experiments

- K-server pipeline-003: the startup proxy reached the pinned controller, but six fast plus three heavy workers caused a confirmed WSL global OOM before any completed stage result (Level 1 runtime evidence).
- K-server pipeline-004: one fast plus three heavy workers reached the controller, then WSL terminated with `Wsl/Service/E_UNEXPECTED` before any completed stage result (Level 1 runtime evidence).
- K-server pipeline-005: one fast plus one worker per heavy stage reached the controller, then WSL again became unresponsive before any completed stage result (Level 1 runtime evidence).
- No k-server candidate was scored in these staged-search runs; no movement below the frozen primary baseline of `3` is claimed.
- Current allocation: `WAITING_FOR_CAPABILITY`; DTS needs a structural decomposition, Heilbronn remains `BLOCKED_FOUNDATION_INTEGRITY`, and k-server needs a stable more-capable runtime or the missing reported 3-violation candidate workspace.
