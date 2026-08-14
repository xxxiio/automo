---
template: milestone-plan
template_version: 2.0.0
project_owned: true
record_contract: milestone-plan
record_schema_version: 1
id: MILESTONE-0016
status: completed
---

# MILESTONE-0016 — Consumer compatibility and project-agent composition hardening

## Intended outcome

Automo can be adopted by a domain package through thin adapters, while project-specific research guidance composes through the same `.project-agent/` extension model used by GetDone dev and mutable research state remains under `.automo/`.

## Why this milestone matters

Pre-alpha review identified extension-contract risks after MILESTONE-0015. The user explicitly approved resolving these before returning to release CI.

## Scope

- Nullable feature-set provenance.
- Heterogeneous model pools.
- Pluggable selectors and structured-calibration boundary.
- Strict `.automo` state schema checks.
- GetDone-style `.project-agent/` composition, validation, inference, opt-out, and lock.
- Agent research-plan conformance checks.
- Real consuming-package compatibility checks.

## Non-goals

- Domain-specific algorithms in Automo.
- Replacing consumer-domain contracts.
- New search breadth or deployment behavior.

## Deliverables

- Updated registry/refresh/runtime contracts.
- Project-agent guidance selection and lock commands.
- Project-agent and consumer-boundary skill documents.
- Research-plan conformance validator.
- M16 compatibility tests and xihbm compatibility evidence.

## Dependencies

- MILESTONE-0015 completed.
- User-approved pre-alpha hardening temporarily superseded MILESTONE-0013 CI execution.

## Risks

- Over-generalizing pools/selectors could break the existing refresh path; backward compatibility is covered by the original refresh suite.
- Project-agent guidance could inflate context; selection remains bounded and additive.

## Ordered implementation sequence

1. Align project-agent parsing and selection with GetDone dev 1.1.2.
2. Add guidance composition locks and strict project-state schema checks.
3. Generalize provenance, pool, selector, and calibration extension contracts.
4. Add agent-plan conformance checks.
5. Validate against the real xihbm project-agent and relevant lifecycle tests.
6. Run full Automo and GetDone validation.

## Exit criteria

- [x] EC-001: Data-only/custom-input models can persist `feature_set_id: null` without sentinels.
- [x] EC-002: Pools can declare multiple comparable model specs and refresh evaluates each retained model with its own spec.
- [x] EC-003: Domain plugins can register a custom selector while built-ins remain backward compatible.
- [x] EC-004: Structured calibration has an explicit extension boundary.
- [x] EC-005: `.automo` rejects unsupported schema versions.
- [x] EC-006: `.project-agent/index.json` schema 1 supports concerns, changed-path inference, path selectors, safe references, and opt-out.
- [x] EC-007: Guidance composition can be pinned and drift-detected.
- [x] EC-008: Agent research-plan conformance rejects unsafe/confounded plans deterministically.
- [x] EC-009: Existing xihbm project-agent guidance works without format migration.
- [x] EC-010: Relevant xihbm lifecycle/selection/research-handoff tests pass.
- [x] EC-011: Full Automo/source/GetDone local validation passes.

## Evidence

- `tests/test_m16_compatibility.py`.
- Full Automo suite: 119 passed.
- xihbm compatibility subset: 19 passed.
- Existing xihbm `.project-agent/index.json` selected successfully with both explicit concern and changed-path inference.
- GetDone dev 1.1.2 validation after record update.

## Remaining work

- None for MILESTONE-0016.
- Full xihbm suite was not executable because `polars` is unavailable in this container; the relevant non-Polars compatibility subset passed.

## Next milestone

MILESTONE-0013 resumes for connected Python 3.11–3.13 CI and pre-commit/Ruff evidence.
