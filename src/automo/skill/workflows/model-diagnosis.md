# Model diagnosis workflow

## Trigger
Use when evidence identifies a performance, calibration, robustness, subgroup, temporal, or refresh problem but the correct intervention is not yet established.

## Procedure
1. State the symptom and exact evidence boundary where it occurs.
2. Compare it with the committed baseline and relevant historical/refresh evidence.
3. Generate the smallest set of competing explanations consistent with the observations.
4. Use the research diagnosis standard and diagnosis patterns to select the cheapest discriminating check.
5. Choose one bounded next action using the intervention decision table.
6. Define what result would falsify the diagnosis.
7. If evidence cannot discriminate explanations, record `inconclusive` and request the missing evidence rather than widening model search.

## Output
Record symptom, competing explanations, evidence, selected diagnosis, falsification condition, and exactly one next action.
