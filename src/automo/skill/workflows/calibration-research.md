# Calibration research workflow

Treat calibration as fitted state independent from the base model. Fit calibration only on its committed fitting partition, gate on validation, freeze it before OOS, and compare both calibration-sensitive metrics and the hypothesis's committed objective. Do not relabel a weak base model as a calibration problem without evidence.
