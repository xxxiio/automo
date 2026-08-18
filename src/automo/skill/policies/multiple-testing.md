# Multiple-testing and selection-bias policy

## Trigger
Apply whenever a research plan evaluates multiple candidates, repeatedly reuses the same validation partition, compares many feature/model variants, or chooses a candidate because it was the best among attempted alternatives.

## Rules
1. Record every attempted candidate and its fingerprint; failed or weak candidates remain part of the evidence history.
2. Commit the candidate-generation rule, validation metric, ranking rule, and maximum candidate count before execution.
3. Do not treat the best validation result from a wide search as equivalent evidence to a pre-specified single comparison.
4. Increase the evidentiary bar as adaptive search breadth grows. Prefer replication across folds/periods or a sealed OOS confirmation over interpreting tiny validation differences.
5. Do not repeatedly inspect sealed OOS to choose among candidates. A consumed OOS slot remains consumed.
6. If the plan changes because results were observed, record a new research plan or hypothesis boundary before continuing.
7. Report the number of attempted, valid, shortlisted, and OOS-evaluated candidates with the conclusion.

## Practical interpretation
Automo does not require one universal statistical correction because objectives and dependence structures vary. It does require transparent search accounting and evidence proportional to selection pressure. Domain plugins may add stronger statistical corrections when appropriate.

## Stop condition
If the remaining expected improvement is smaller than the uncertainty introduced by repeated selection, stop and conclude inconclusive or plan a genuinely new data/evidence boundary.
