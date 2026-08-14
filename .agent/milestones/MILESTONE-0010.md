---
template: milestone-plan
template_version: 2.0.0
project_owned: true
record_contract: milestone-plan
record_schema_version: 1
id: MILESTONE-0010
status: completed
---

# Milestone: Model pool and data-iteration refresh lifecycle

## Intended outcome

Automo safely refreshes retained compatible models against immutable data iterations, including governed recalibration/retraining and persisted pool selection, without requiring datetime data.

## Why this milestone matters

The model registry retains reconstructable artifacts; recurring data updates need equally reusable evaluation, recalibration, retention, and selection infrastructure.

## Scope

- Dataset-agnostic partition strategies.
- Data iterations, refresh scorecards, model pools and snapshots.
- Separate training/calibration/retention/selection policies.
- Recalibration and retraining through fit/validation/refresh-OOS.
- Refresh/pool CLI and history.

## Non-goals

- Open-ended candidate search, deployment, online learning, contextual bandits, feature-distribution drift detection.

## Deliverables

- `src/automo/refresh/` runtime.
- Plugin extension points for pools/calibrators/splits.
- `automo refresh` and pool inspection CLI.
- `docs/refresh.md` and tests.

## Dependencies

- MILESTONE-0009.

## Risks

- Adaptive reuse of refresh evidence is distinguished from sealed research OOS.
- Fitted-state changes must never touch refresh-OOS before validation freeze.

## Ordered implementation sequence

1. General partition/data-iteration contracts.
2. Policy and pool contracts.
3. Recalibration/retraining evaluation runtime.
4. Retention and selection.
5. Persisted history and CLI.
6. Documentation and acceptance gates.

## Exit criteria

- [x] EC-001: Dataset-agnostic immutable iterations.
- [x] EC-002: General split protocols.
- [x] EC-003: Governed refresh evaluation.
- [x] EC-004: Governed recalibration.
- [x] EC-005: New identity on retraining.
- [x] EC-006: Persisted model pools.
- [x] EC-007: Independent policies.
- [x] EC-008: Evidence-backed retention/selection.
- [x] EC-009: Immutable history.
- [x] EC-010: User-facing refresh/pool UX.

## Evidence

- `tests/test_refresh.py` and `docs/refresh.md`.

## Remaining work

- None.

## Next milestone

MILESTONE-0011
