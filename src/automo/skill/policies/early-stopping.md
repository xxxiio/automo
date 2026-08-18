# Research early-stopping policy

A research budget is a maximum, not a quota. Stop before exhausting it when continuing has low decision value.

## Stop early when
- the active hypothesis is falsified by evidence strong enough to satisfy its rejection criteria;
- two or more independent bounded interventions reproduce the same material failure and no unresolved diagnostic alternative would change the decision;
- all remaining candidates are dominated by already evaluated candidates under the committed decision rule;
- the remaining OOS budget would be spent only to rescue a weak validation story;
- a required capability or data boundary is unavailable and cannot be resolved within the hypothesis scope;
- repeated candidates produce diminishing improvements below the precommitted materiality threshold;
- continuing would require changing the hypothesis, objective, split protocol, or search boundary.

## Do not stop merely because
- the first candidate failed;
- a preferred model underperformed;
- a result is inconvenient;
- validation variance is high but the plan explicitly requires another independent replication.

## Required output
Record the stop reason, evidence that activates it, unused budget, and whether the hypothesis should conclude or another bounded experiment is justified.
