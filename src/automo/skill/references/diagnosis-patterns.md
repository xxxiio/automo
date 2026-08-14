# Diagnosis patterns

These patterns generate hypotheses; they are not conclusions by themselves.

- Validation strong, OOS weak: investigate overfit, instability, leakage, selection bias, or distribution shift before more tuning.
- Ranking/discrimination strong, calibration weak: consider calibration research while holding base predictions fixed.
- All candidates weak: revisit data, target/objective, feature information, split design, or model family rather than increasing search width.
- Recent refresh degradation with previously stable research evidence: investigate staleness/drift and data-iteration changes before declaring the original hypothesis false.
- Improvement isolated to one fold/subgroup/period: require stability evidence and an explanatory interaction before generalizing.
- Training metric improves while validation is flat: investigate capacity, variance, leakage, or objective mismatch; do not reward training fit.
- Validation differences are tiny relative to fold/period variation: treat ranking as uncertain and reduce selection pressure rather than declaring a winner.
- Calibration improves but downstream objective worsens: optimize the downstream decision objective and treat calibration as a component, not an unconditional goal.
- Strong historical model plus simultaneous degradation across retained models: prioritize data/market/environment shift diagnosis over independent model replacement.
