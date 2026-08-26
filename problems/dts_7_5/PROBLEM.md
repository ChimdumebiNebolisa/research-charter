# Minimum-scope `(7,5)` Difference Triangle Set

## Frozen question

Construct an array with seven rows and six integer entries per row,

```text
0 = a[i,0] < a[i,1] < ... < a[i,5]
```

such that every positive difference `a[i,j] - a[i,j']` for `j' < j` is distinct across all rows. There are `7 * binomial(6,2) = 105` such differences. The scope is `max(a[i,j])`.

The true objective is to minimize scope. The frozen strict-improvement target is a valid scope `<=111`, against the published scope-112 construction.

## Objective versus evaluator

The mathematical object is the integer DTS itself. The integer validator checks the defining conditions and scope; it does not make the problem easier by checking only a subset, allowing repeated differences, or treating a different modular object as equivalent.

The problem is related to Golomb rulers and coding applications, but those related structures are not substitutes for this exact `(7,5)` DTS question.

## Evidence boundaries

A valid scope-111 or lower witness is primary-evaluator progress. A record claim additionally requires an independent clean-checkout validation and a provenance/prior-art review. A search heuristic that reduces a proxy or finds a partial row is Level 1 only.

## Primary sources and provenance

- [Shehadeh, Kingsford, and Kschischang, *New Difference Triangle Sets by an FPGA-Based Search Technique*](https://doi.org/10.1002/jcd.22009), Journal of Combinatorial Designs 34(1), 2026, §2 and Table 1. Table 1 reports `m(7,5) <= 112` with previous upper bound `113`; Appendix A gives the construction.
- [arXiv:2502.19517](https://arxiv.org/abs/2502.19517), the accessible prepublication record of the same work.
- [dts-search-hdl](https://github.com/applecoffeecake/dts-search-hdl), pinned in `upstreams.lock.json` as optional upstream search provenance, not as a mutable validator.
