# Heilbronn Verification Contract

An independent verifier must:

1. require exactly 12 distinct points, each coordinate in the closed interval `[0,1]`;
2. enumerate all 220 triples;
3. compute each doubled determinant and area, identifying zero or collinear triples;
4. determine the minimum area without silently rounding it upward;
5. compare the minimum to the exact algebraic Comellas–Yebra baseline or to a certified interval that proves a strict positive gap;
6. record the arithmetic method, precision/certificates, coordinates, minimum triangle(s), and any symmetry or degeneracy.

Float64-only improvement is exploratory evidence. A strict record requires higher precision, exact symbolic comparison, interval certification, or an equivalent independent method appropriate to the coordinate representation. No finite configuration can prove the global Heilbronn optimum unless a separate mathematical proof establishes the needed upper bound.
