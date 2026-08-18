# Intervention decision table

Use this as a decision aid after diagnosis, not as an automatic rule.

| Evidence pattern | Prefer first | Avoid first |
|---|---|---|
| ranking/discrimination stable, calibration weak | recalibration | replacing the whole base model |
| validation strong, OOS weak | leakage/stability/search-bias diagnosis | wider hyperparameter search |
| all models weak | data/objective/feature-information investigation | tuning one family more aggressively |
| historical model strong, latest refresh weak | refresh/drift analysis | declaring the research hypothesis false |
| subgroup weakness with stable overall metric | subgroup/interaction diagnosis | global model replacement without attribution |
| candidate gains vanish across periods | robustness/temporal analysis | promotion on aggregate validation alone |
| meta-model improves only with one upstream input | ablation/incremental-value test | adding more upstream outputs simultaneously |
| train metric improves, validation flat | capacity/variance/objective diagnosis | more capacity |
| calibration metric improves but downstream utility falls | objective-specific evaluation | promoting on calibration metric alone |

A selected intervention must still satisfy the active hypothesis, declared search space, budget, and evidence policies.
