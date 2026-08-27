# Scoreboard

This is a derived summary, not the source of scientific truth. It is updated from the append-oriented experiment records.

| Problem | Frozen baseline | Target | Foundation status |
| --- | --- | --- | --- |
| `dts_7_5` | scope `112` | scope `<=111` | baseline independently verified; no improving candidate; direct, local, global, FPGA, and tested structured families closed; search PAUSED |
| `heilbronn_n12` | source-faithful `0.032598858691819698...` | certified minimum area strictly greater | search BLOCKED: protected Markdown transcription yields zero area |
| `kserver_k4_circle` | reported `3` violations on pinned `circle_taxi_k4_m6.pickle` | fewer than `3` | pinned evaluator independently reproduces `5` for upstream seed vector 0; target not reached; reported 3-vector absent |

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

## Phase 2 evidence after twenty-nine substantive experiments

- DTS single-anchor difference allocation: 44,378 deduplicated conditional rows reached depth 5, matching the prior ceiling (Level 1 finite-family evidence).
- DTS rejection-based pair allocation: generation exhausted its budget before exact-cover search (Level 1 implementation failure).
- DTS incremental pair allocation: 14,397 masks were generated, but exact-cover search again received zero nodes (Level 1 implementation failure).
- DTS valid-row library packing: best union 96/105; conflict-directed library swaps: best union 97/105. Both best states failed the independent integer verifier (Level 1 finite-family evidence).
- No true-objective movement has been verified. Current allocation remains `WAITING_FOR_CAPABILITY`; the next valuable action is a genuinely new algebraic/structured DTS construction or exact decomposition.

## Phase 2 evidence after thirty-two substantive experiments

- DTS public FPGA-reference adaptation: with separated training (TRAINING_M=152, 100 trials), the source-faithful default-threshold run reached main search but repeatedly stalled at six populated rows; no scope-111 candidate was decoded (Level 1 finite runtime evidence).
- DTS FPGA threshold variant: increasing BLOCK_GEN_THRESH to 1000 and DTS_GEN_THRESH to 2000000 completed training but consumed the 120-second software budget before any main-search status; no candidate was decoded (Level 1 finite runtime evidence).
- These FPGA runs test a public bit-parallel search family and provide capability/runtime information only; they do not establish infeasibility or novelty. No true-objective movement has been verified.
- Current allocation remains `WAITING_FOR_CAPABILITY`: DTS now needs hardware-scale FPGA execution or a genuinely new algebraic/structured decomposition; Heilbronn remains `BLOCKED_FOUNDATION_INTEGRITY`; k-server remains runtime/candidate-provenance blocked.

## Phase 2 evidence after thirty-seven substantive experiments

- DTS affine gap coupling: best `89/105` unique differences; no valid target.
- DTS quadratic gap coupling: best `79/105` unique differences; no valid target.
- DTS exhaustive p=43 Ruzsa/Ling residue split: `10,922,688` balanced transforms; best independently valid scope `195`; no target transform.
- K-server single-process shared circle cache: cache built and 700 exact circle candidates completed, including zero-violation circle proxies; full taxi evaluation exceeded the local wall budget.
- K-server streaming full-metric evaluator: the first pinned upstream seed vector scored `5` over all `7,000,602` taxi inequalities in `528` seconds; the unmodified pinned evaluator independently reproduced `5` in `495` seconds with eight final workers. This is finite primary-metric movement from the local 17-violation parametrized baseline, not the frozen target and not a novel candidate because the vector is present in the pinned source.
- Current allocation: `WAITING_FOR_CAPABILITY` for further full-metric search unless a targeted mutation run is preregistered; DTS structured families remain closed; Heilbronn remains `BLOCKED_FOUNDATION_INTEGRITY`.

## Phase 2 evidence after thirty-nine substantive experiments

- K-server targeted five-edge repair: 380 of 1,831 generated mutations were screened before the wall budget; coefficient-8 replacements had zero residuals on the five known seed-failing edges (Level 1 proxy only).
- The two top proxy finalists were exact-scored on all `7,000,602` taxi inequalities and both returned `348,550` violations. The local five-edge repair proxy is falsified and closed; no target result is claimed.
- The upstream seed vector remains the best locally verified finite result at `5` violations, independently reproduced by the unmodified pinned evaluator; it is upstream-listed and not a novelty claim.
- Current allocation: `WAITING_FOR_CAPABILITY` for a globally cached/vectorized candidate screen or more capable runtime; do not repeat the five-edge proxy.
