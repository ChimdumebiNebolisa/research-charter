# Frozen DTS Baseline

Status: `RESOLVED_PUBLISHED_UPPER_BOUND`.

The frozen baseline is:

```text
problem_id: dts_7_5
metric: scope
direction: minimize
published_valid_construction_scope: 112
previous_best_published_upper_bound: 113
target: scope <= 111
```

The 2026 Journal of Combinatorial Designs article reports the definition of `m(n,k)`, its Table 1 reports `112` for row `k=5`, column `n=7`, and the previous value `113` in parentheses. Its Appendix A contains the explicit witness. The target is therefore strict integer improvement by at least one scope unit.

This foundation does not assert that scope 112 is globally optimal; it freezes the best verified published upper-bound construction relevant to the requested target. Any later claim must provide the exact witness and independent validation.

Primary reference: [DOI 10.1002/jcd.22009](https://doi.org/10.1002/jcd.22009), §2, Table 1, Appendix A.
