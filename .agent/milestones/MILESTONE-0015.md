---
template: milestone-plan
template_version: 2.0.0
project_owned: true
record_contract: milestone-plan
record_schema_version: 1
id: MILESTONE-0015
status: completed
---

# MILESTONE-0015 — Research guidance completeness and agent safety

## Intended outcome

Automo's agent-facing research guidance is complete enough for the first public alpha: agents receive bounded procedures for diagnosis, experiment design, multiple testing, early stopping, meta-model ablation, refresh decisions, inconclusive evidence, and safe capability escalation.

## Why this milestone matters

MILESTONE-0014 established governance and guidance routing, but pre-alpha review identified that the content needed deeper research methodology and executable reliability checks before external agents should rely on it.

## Scope

- Richer diagnosis and intervention-selection guidance.
- Multiple-testing/selection-bias and early-stopping policies.
- Stronger meta-model OOF, ablation, incremental-value, and complexity rules.
- Refresh-versus-new-research guidance.
- Agent adherence failure scenarios.
- Deterministic guidance-pack validation and CLI drift tests.
- Synthetic multi-milestone research walkthrough.

## Non-goals

- New model algorithms, broader automated search, domain-specific methodology, statistical guarantees for every objective, or automatic interpretation of arbitrary natural-language tasks.

## Deliverables

- Expanded `src/automo/skill/` standards/policies/references/workflows/acceptance.
- `validate_guidance_pack()` deterministic guidance validation.
- `examples/research-guidance/` multi-milestone walkthrough.
- `tests/test_research_guidance_completeness.py`.
- Updated agent-guidance documentation.

## Dependencies

- MILESTONE-0014 completed.

## Risks

- Guidance can become too large; selection-size validation keeps task context bounded.
- Research advice can overclaim statistical certainty; policies require transparent selection accounting and allow inconclusive outcomes.

## Ordered implementation sequence

1. Deepen diagnosis and intervention rules.
2. Add multiple-testing and early-stop policies.
3. Strengthen meta-model and refresh guidance.
4. Add negative agent-adherence scenarios.
5. Add skill-pack/CLI contract validation.
6. Add a synthetic sequential research walkthrough and run full regression.

## Exit criteria

- [x] EC-001: Every supported task class resolves to a bounded, valid guidance set.
- [x] EC-002: Experiment/search guidance explicitly covers multiple testing and selection bias.
- [x] EC-003: Milestone/experiment guidance defines diminishing-return and evidence-based early stopping.
- [x] EC-004: Diagnosis covers overfit, leakage, instability, calibration, drift, subgroup, objective, and data-quality failure modes.
- [x] EC-005: Meta-model guidance requires OOF/cross-fitting, matched ablation, incremental-value evidence, and safe graph-depth handling.
- [x] EC-006: Guidance distinguishes refresh/recalibration/retraining from genuinely new research.
- [x] EC-007: Agent-adherence gates reject sealed-OOS selection, hidden failed candidates, unplanned search expansion, and confounded interventions.
- [x] EC-008: Guidance CLI references are tested against the real Typer command tree.
- [x] EC-009: A synthetic multi-milestone walkthrough covers accepted and rejected research outcomes without violating budgets/OOS rules.
- [x] EC-010: Full local regression passes after the guidance expansion.

## Evidence

- `tests/test_research_guidance_completeness.py`.
- `examples/research-guidance/`.
- `src/automo/skill/policies/multiple-testing.md` and `early-stopping.md`.
- `src/automo/skill/standards/diagnosis.md`.
- Expanded meta-model/refresh/experiment workflows and agent-adherence gate.
- `python -m pytest -q`: 110 passed.

## Remaining work

- None for this milestone.

## Next milestone

MILESTONE-0013 resumes for connected CI/pre-commit release evidence.
