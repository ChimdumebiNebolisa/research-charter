# 12-point Heilbronn Configuration

## Frozen question

Place exactly 12 distinct points in the unit square `[0,1]^2` to maximize the smallest area among the `binomial(12,3) = 220` triangles determined by triples of points. If points `p_i=(x_i,y_i)`, the doubled area of a triple is the absolute determinant

```text
| (x_j-x_i)(y_k-y_i) - (x_k-x_i)(y_j-y_i) |.
```

The true objective is the maximum possible minimum triangle area. The frozen strict-improvement target is a rigorously checked configuration whose minimum area is strictly greater than the exact Comellas–Yebra construction baseline.

## Objective versus evaluator

The mathematical object is a 12-point configuration in the unit square. The evaluator enumerates the 220 triangles and computes their minimum area. A local maximum, a float64 score, a subset of triangles, or an approximate optimizer output is not by itself a research result.

The published 12-point result is a lower-bound construction. It is not a theorem that no better configuration exists. The 2026 certification paper proves optimality only through `n=9` and explicitly treats `n=10` through `n=12` as heuristic best-known configurations. This makes rigorous comparison and careful wording essential.

## Evidence boundaries

Float64 movement is at most Level 1 until confirmed with exact, interval, or otherwise certified arithmetic. A candidate that beats the baseline under certified arithmetic is Level 2/3 depending on independent reproduction, but it is not a proof of global optimality or a theorem about the asymptotic Heilbronn problem.

## Primary sources

- [Comellas and Yebra, *New Lower Bounds for Heilbronn Numbers*](https://doi.org/10.37236/1623), Electronic Journal of Combinatorics 9(1), R6 (2002), §3. This source defines `H_n`, gives the 12-point coordinates, and reports `H12 >= 0.032599`.
- [Comellas–Yebra PDF](https://www.emis.de/ft/5926), §3, page 7 of the PDF. The authors state that their values for `7 <= n <= 12` were not proved optimal.
- [Sudermann-Merx, *From Computational Certification to Exact Coordinates*](https://arxiv.org/abs/2603.11107), 2026, §1.3 and Appendix A. It certifies smaller cases and identifies the 10–12 configurations as heuristic best-known values.
- [Erich Friedman's current square record page](https://erich-friedman.github.io/packing/heilbronn/), record index retrieved 2026-08-26; it lists the 12-point value as approximately `0.03260` and attributes it to Comellas and Yebra.
