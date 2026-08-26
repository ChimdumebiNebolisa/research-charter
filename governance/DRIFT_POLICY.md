# Drift Policy

Research drift is any movement away from a frozen question, target, evaluator, or evidence standard, whether explicit or gradual.

## Obvious drift

- adding a problem;
- changing a problem identifier, target, benchmark, or success threshold;
- substituting a related but easier benchmark;
- modifying a frozen baseline or validator.

## Subtle drift

- optimizing a proxy indefinitely without showing its connection to the true objective;
- spending large compute after a direction stopped producing information;
- turning infrastructure work into the project;
- repeatedly polishing code instead of testing a hypothesis;
- replacing an unsuccessful question with a neighboring question;
- mistaking more runs for more knowledge;
- continuing a direction solely because effort has already been invested;
- treating evaluator exploitation or a numerical artifact as scientific progress.

Every record must map to exactly one frozen `problem_id` and its frozen `target_id`. The drift checker rejects missing or mismatched mappings, missing objective relations, duplicate experiments without justification, and unknown record types. A problem with unresolved foundations is blocked from research until a human resolves it.
