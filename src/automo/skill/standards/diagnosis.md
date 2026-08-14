# Research diagnosis standard

## Purpose
Convert observed evidence into a bounded diagnosis before choosing an intervention. A diagnosis is a testable explanation of the observed failure mode, not a justification for trying a preferred model.

## Required evidence classes
Use only evidence whose provenance and evaluation boundary are known. Distinguish fit, validation, research OOS, refresh OOS, subgroup, temporal, calibration, and operational evidence. Do not merge these classes into one score without an explicit aggregation rule.

## Diagnostic procedure
1. State the observed symptom and the evidence partition where it occurs.
2. Compare against the committed baseline and any relevant historical evidence.
3. List the smallest plausible competing explanations.
4. Identify the observation that would discriminate between those explanations.
5. Select the lowest-cost bounded intervention or diagnostic experiment that can resolve the uncertainty.
6. If available evidence cannot distinguish the explanations, conclude `inconclusive` and gather the missing evidence rather than expanding model search.

## Common failure modes
- **Validation improvement, OOS deterioration:** suspect overfit, search selection bias, instability, leakage, or distribution shift before further tuning.
- **Strong ranking/discrimination, weak calibration:** prefer calibration research while holding base predictions fixed.
- **Broad weakness across model families:** investigate data quality, target/objective construction, feature information, split design, or capability limitations before hyperparameter expansion.
- **Recent degradation after previously stable evidence:** distinguish data staleness/drift from structural model failure using refresh evidence.
- **Improvement concentrated in one fold, period, or subgroup:** treat as instability until replicated or explained by a declared interaction.
- **Training improvement without validation movement:** stop capacity/search expansion and investigate variance, leakage, or objective mismatch.
- **Calibration improvement with downstream objective degradation:** reject calibration as a universal improvement; evaluate the actual downstream decision objective.

## Required output
A diagnosis must contain the symptom, competing explanations, supporting evidence, missing evidence, selected next action, and a falsification condition.
