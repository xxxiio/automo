---
template: milestone-report
template_version: 2.0.0
project_owned: true
record_contract: milestone-report
record_schema_version: 1
id: MILESTONE-0012
status: completed
---

# MILESTONE-0012 — Custom training and composable model graphs

## Outcome

Automo supports generic custom training/evaluation contracts, structured model outputs, composable model DAGs, and leakage-safe cross-fitted upstream predictions for downstream/meta-model training without domain-specific core semantics.

## Exit criteria

- [x] EC-001: Full custom trainer hook through `TrainingRequest` / `TrainingResult`.
- [x] EC-002: Training requests receive only the caller-controlled fit partition.
- [x] EC-003: Generic evaluators can use structured outcomes and injected services without a numeric target.
- [x] EC-004: Model outputs can contain structured values through `ModelOutputBatch`.
- [x] EC-005: Model nodes can consume feature/data inputs or upstream model outputs.
- [x] EC-006: Downstream/meta-model fitting uses deterministic cross-fitted upstream outputs.
- [x] EC-007: Validation/OOS graph prediction uses frozen full-fit upstream/downstream predictors.
- [x] EC-008: Graph registry provenance records graph id, upstream registered identities, and cross-fit protocol.
- [x] EC-009: Research interventions can change graph node models and upstream model-output inputs.
- [x] EC-010: A synthetic external-service trainer/evaluator example runs without domain-specific dependencies.
- [x] EC-011: Synthetic onboarding examples cover supervised, custom trainer, meta-model, structured output, and ID-only data paths.

## Evidence

See `src/automo/runtime/contracts.py`, `src/automo/runtime/graph.py`, `src/automo/research/graph.py`, `tests/test_graph_runtime.py`, `tests/test_examples.py`, `docs/trainers-and-graphs.md`, and `examples/`.

## Risks

Nested model-output cross-fitting beyond one upstream stacking layer is intentionally rejected in the first graph runtime contract rather than being executed unsafely.
