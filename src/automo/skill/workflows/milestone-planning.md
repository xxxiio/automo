# Milestone planning workflow

## Trigger
Use when `.automo/project.yaml` is in plan mode.

## Inputs
Roadmap, prior milestones, findings, model-pool/refresh evidence, available data/capabilities, previous attempted candidates, and remaining OOS budget.

## Procedure
1. Identify the highest-value unresolved research question.
2. Explain why it outranks other unfinished questions using decision value, uncertainty, expected information gain, cost, and dependency ordering.
3. Check whether the observed problem is actually an operational refresh/recalibration issue rather than a new research question.
4. Define one bounded milestone question, binary exit criteria, non-goals, candidate/fit/cost/OOS budgets, and a materiality threshold.
5. Precommit the evidence boundary, candidate-selection rule, and multiple-testing treatment.
6. Define early-stop conditions for accepted, rejected, inconclusive, invalid, blocked, and diminishing-return outcomes.
7. Prefer a milestone that can be falsified or concluded inconclusive; never define success-only criteria.
8. Approve and activate only after data, split protocol, evidence boundaries, safeguards, and stop conditions are fixed.

## Forbidden
Do not run training, validation search, or sealed OOS while planning. Do not choose a milestone solely because a preferred algorithm is available.
