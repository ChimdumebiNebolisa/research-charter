# DTS Verification Contract

An independent verifier must:

1. require exactly seven rows and exactly six entries per row;
2. require integer entries, first entry zero, nonnegative entries, and strict increase within each row;
3. enumerate all 105 positive within-row differences and reject any duplicate;
4. compute the scope as the maximum entry using integer arithmetic;
5. report the complete witness, difference count, duplicate set (if any), and scope;
6. compare a claimed strict improvement to the frozen scope-112 baseline as `scope <= 111`.

The public upstream search implementation is not the final verification authority for a new result. Search code may be replaced; this contract may not be weakened during ordinary research. A candidate that is valid but has scope 112 or greater is partial or non-improving progress, not a strict improvement.
