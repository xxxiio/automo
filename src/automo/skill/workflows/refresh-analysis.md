# Refresh analysis workflow

## Purpose
Determine whether new data requires operational model lifecycle action or a new research question.

## Procedure
1. Compare retained models on the new immutable data iteration using the declared refresh split.
2. Separate calibration drift, ranking/objective drift, data-quality changes, and broad environment shift.
3. If a previously strong model remains structurally useful but calibration moved, prefer bounded recalibration.
4. If model performance decays with staleness while the research hypothesis remains supported, prefer retraining/refresh.
5. If several retained models degrade together, investigate data/environment shift before independent model replacement.
6. Open a new research milestone only when refresh evidence identifies a structural unresolved question that operational refresh cannot answer.
7. Preserve refresh OOS as lifecycle evidence; do not silently reuse it as a candidate-generation validation set.
