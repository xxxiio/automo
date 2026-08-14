# Meta-model patterns

## Incremental-value question
For each upstream model output, ask whether it contributes information to the final downstream objective beyond the already selected inputs. Do not justify an input merely because its standalone metric is strong.

## Required comparisons
Prefer one of these bounded comparisons:
- add one upstream output while holding all other nodes fixed;
- remove one upstream output while holding all other nodes fixed;
- replace one upstream model/version while preserving the downstream definition;
- compare a meta-model against the strongest simpler baseline that has access to the same non-model features.

## OOF requirement
During downstream fitting, upstream predictions for fit rows must be out-of-fold/cross-fitted. Validation and OOS use frozen full-fit upstream models. In-sample upstream predictions are leakage unless the upstream model is provably independent of those rows.

## Attribution
An improvement belongs to the graph intervention only if versions, calibrations, data boundaries, and unrelated inputs are controlled. If both an upstream model and downstream architecture change, the result is confounded unless the plan explicitly defines a factorial comparison.

## Ablation gate
Before promoting a more complex graph, demonstrate that the added node/input provides material incremental value or a required operational property. If its removal does not materially degrade the committed objective, prefer the simpler graph.

## Nested graph limit
If the runtime cannot safely cross-fit the required dependency depth, stop with an explicit unsupported-capability result. Never substitute in-sample predictions to make the experiment run.
