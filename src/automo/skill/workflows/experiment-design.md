# Experiment design workflow

## Inputs
Active milestone, current diagnosis, baseline, declared search space, data/split protocol, prior candidate fingerprints, remaining budget, and OOS boundary.

## Procedure
1. State one falsifiable hypothesis tied directly to the milestone question.
2. Select one conceptual intervention; keep unrelated model, feature, calibration, and data choices fixed unless the plan explicitly defines a factorial experiment.
3. Define the baseline, candidate, primary decision metric, materiality threshold, and required stability/subgroup checks before fitting.
4. Record the candidate-generation rule and maximum number of attempted variants.
5. Define fit/validation/OOS roles and whether this experiment is permitted to consume an OOS slot.
6. Define acceptance, rejection, invalidation, and inconclusive conditions.
7. Check the fingerprint history and capability availability before execution.
8. Apply the multiple-testing policy when more than one candidate or adaptive iteration is possible.
9. Define early-stop conditions and the one next action for each possible outcome class.

## Forbidden
Do not use sealed OOS to create candidates, expand search after seeing weak results, omit failed candidates, or change several conceptual dimensions merely to improve the score.
