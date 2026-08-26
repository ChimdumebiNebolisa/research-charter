# Frozen Heilbronn `n=12` Baseline

Status: `RESOLVED_CREDIBLE_CONSTRUCTION_NOT_GLOBAL_OPTIMUM`.

The frozen construction is the completely symmetric 12-point configuration from Comellas and Yebra. Let

```text
A = 27 + 3*sqrt(57)
x = 1 - (A^(2/3) + 6)/(6*A^(1/3))
y = 2*x^2 - 3*x + 1/2
```

with the real values `x ≈ 0.115354` and `y ≈ 0.180552`. The twelve points are:

```text
(0,0)       (1-x,0)      (0,x)       (1,x)
(1/2,y)     (y,1/2)      (1-y,1/2)   (1/2,1-y)
(0,1-x)     (1,1-x)      (x,1)       (1-x,1)
```

The published minimum-area lower bound is

```text
B_H12 = x/4 + x*y/2 - x^2/2 ≈ 0.032599.
```

Frozen target: prove, with exact or certified arithmetic, a 12-point configuration whose minimum of all 220 triangle areas is strictly greater than `B_H12`. A float64 value that is only numerically above a rounded `0.032599` is not sufficient.

The source explicitly says it has no proof of optimality for these new bounds. Accordingly, this baseline is a credible published construction, not a certified global optimum. No `BASELINE_UNRESOLVED` flag is required for the construction target, but the global-optimum question remains open and must not be silently substituted for the frozen improvement target.

Primary reference: [Comellas and Yebra (2002), §3](https://www.emis.de/ft/5926).
