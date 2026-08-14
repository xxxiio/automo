# Agent research adherence gate

An agent-driven research action passes this gate only when all applicable conditions hold.

## Pass conditions
- The current research milestone is active before execution.
- The action answers the active milestone question and stays inside declared non-goals.
- The intervention is falsifiable and changes only the conceptual dimensions justified by the plan.
- Candidate, fit, runtime/cost, and OOS budgets are respected.
- All attempted candidates are recorded; duplicates are rejected by fingerprint.
- Fit/validation/OOS roles are preserved and sealed OOS is not used for candidate generation.
- Meta-model training uses OOF/cross-fitted upstream outputs where required.
- Conclusions distinguish accepted, rejected, inconclusive, and invalid outcomes.
- Exactly one justified next research step is recorded, or the milestone is concluded.

## Automatic failure scenarios
- Expanding search because observed results are disappointing without a new approved plan.
- Inspecting sealed OOS to select a candidate or tune a threshold.
- Omitting failed candidates from the research history.
- Changing objective, split protocol, feature family, and model family together without a predeclared factorial design.
- Implementing a missing software capability ad hoc instead of producing a bounded capability request.
- Promoting a meta-model without an ablation that establishes incremental value of the changed upstream input/node.
- Declaring success from a metric that is not the committed decision objective.
