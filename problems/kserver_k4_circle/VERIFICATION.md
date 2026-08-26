# k-server Verification Contract

An independent evaluation must:

1. use an unmodified clean checkout of `k-server-bench` at commit `aea64346b846c967e4448f098d4b8b1748504d27`;
2. use the upstream `tools/evaluator/evaluate.py` and the unmodified `circle_taxi_k4_m6.pickle` metric file;
3. instantiate the submitted `Potential` through the upstream interface;
4. count `violations_k` across all `7,000,602` checked inequalities and preserve the raw evaluator output;
5. compare the count to the frozen baseline of 3, requiring an integer count `<3` for primary improvement;
6. where a candidate claims generality, additionally evaluate the full four-file suite from the pinned k4 task hint;
7. run from a clean environment and preserve dependency versions, commit SHA, metric hashes, command line, and candidate artifact.

The evaluator's finite result is not a proof of the full k-server conjecture. Independent and adversarial checks must look for metric leakage, hard-coded outputs, altered tolerances, incomplete instance coverage, and candidate code that mutates benchmark infrastructure. An evaluator loophole is not automatically a mathematical solution.
