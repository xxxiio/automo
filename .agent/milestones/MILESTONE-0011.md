---
template: milestone-report
template_version: 2.0.0
project_owned: true
record_contract: milestone-report
record_schema_version: 1
id: MILESTONE-0011
status: completed
---

# MILESTONE-0011 — Bounded automated research and interventions

## Outcome

Automo can deterministically generate, budget, evaluate, audit, and retain bounded research candidates without using sealed research-OOS for candidate generation or automatically activating accepted models.

## Exit criteria

- [x] EC-001: Explicit baseline-plus-intervention candidates.
- [x] EC-002: Declarative bounded research spaces.
- [x] EC-003: Evidence-directed candidate generation.
- [x] EC-004: Enforced research budgets.
- [x] EC-005: Validation before sealed OOS.
- [x] EC-006: Multiple-testing exposure evidence.
- [x] EC-007: Duplicate candidate protection.
- [x] EC-008: Model/feature/parameter/calibration interventions.
- [x] EC-009: Immutable registry handoff without activation.
- [x] EC-010: Missing-capability request integration.
- [x] EC-011: Complete research CLI and documentation.

## Evidence

See `.agent/current/evidence.md`, `tests/test_research.py`, `src/automo/research/`, and `docs/research.md`.

## Risks

Validation remains adaptive evidence; sealed research-OOS must stay bounded and must not feed same-iteration candidate generation.
