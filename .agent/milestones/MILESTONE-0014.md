---
template: milestone-plan
template_version: 2.0.0
project_owned: true
record_contract: milestone-plan
record_schema_version: 1
id: MILESTONE-0014
status: completed
---

# MILESTONE-0014 — Agent research guidance and governance

## Intended outcome

Automo provides a bounded research-governance and guidance layer for AI agents while remaining standalone and composing cleanly with optional GetDone development workflows.

## Why this milestone matters

The public-alpha candidate already had deterministic research execution, but an agent still lacked a canonical procedure for choosing research questions, planning milestones, handling OOS boundaries, and escalating missing software capabilities.

## Scope

- `.automo/` research project state and milestone lifecycle.
- Plan mode and execution guard.
- Packaged research guidance selected by `automo guidance`.
- Optional GetDone handoff with strict `.automo/`/`.agent/` ownership separation.
- Documentation and tests.

## Non-goals

- New algorithms, deployment, domain-specific guidance, or automatic mutation of GetDone `.agent/` records.

## Deliverables

- `src/automo/governance.py`
- `src/automo/guidance.py` and `src/automo/skill/`
- research milestone/guidance/capability-handoff CLI
- governance/guidance docs and tests

## Dependencies

- MILESTONE-0012 completed.

## Risks

- Guidance must remain aligned with executable CLI/contracts; packaging tests guard installed availability.

## Ordered implementation sequence

1. Define `.automo/` governance contracts.
2. Add milestone lifecycle and execution guard.
3. Add task-specific research skill pack and guidance selector.
4. Move capability research state under `.automo/` and add explicit GetDone handoff.
5. Document and validate installed behavior.

## Exit criteria

- [x] EC-001: Fresh init creates `.automo/` governance.
- [x] EC-002: Research milestones have deterministic lifecycle/outcomes.
- [x] EC-003: Plan mode blocks research execution.
- [x] EC-004: Agent guidance is minimal and task-specific.
- [x] EC-005: Guidance covers the principal research workflows and safety boundaries.
- [x] EC-006: Capability state is owned by `.automo/`.
- [x] EC-007: GetDone handoff preserves `.agent/` ownership.
- [x] EC-008: Public docs cover the feature.
- [x] EC-009: Regression and package smoke evidence pass.

## Evidence

- `tests/test_governance_guidance.py` and full 102-test regression.
- Installed-wheel `automo guidance --task-class meta-model-research --paths-only` smoke.
- `docs/research-governance.md` and `docs/agent-guidance.md`.

## Remaining work

- None for this milestone.

## Next milestone

MILESTONE-0013 resumes for connected release CI evidence.
