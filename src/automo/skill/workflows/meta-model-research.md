# Meta-model research workflow

## Leakage rule
Any downstream node trained from upstream model outputs must receive out-of-fold/cross-fitted outputs on the fit partition. Validation and OOS use frozen full-fit upstream predictors.

## Procedure
1. State the downstream objective and strongest simpler baseline.
2. Define the upstream output/node whose incremental value is being tested.
3. Prefer add-one, remove-one, or replace-one interventions; hold unrelated node versions, calibrations, and non-model features fixed.
4. Commit the cross-fit protocol before fitting and verify the runtime supports the dependency depth.
5. Evaluate the final downstream objective, not only intermediate upstream metrics.
6. Run an ablation or matched control sufficient to attribute any improvement to the graph change.
7. Apply multiple-testing accounting if several upstream outputs/nodes are screened.
8. Reject added complexity when material incremental value is not demonstrated.
9. Stop with an explicit capability request if safe cross-fitting cannot be represented; never fall back to in-sample upstream predictions.

## Required evidence
Graph/node identities, upstream model versions, calibration identities, cross-fit protocol, baseline comparison, ablation result, final-objective evidence, and complexity disposition.
