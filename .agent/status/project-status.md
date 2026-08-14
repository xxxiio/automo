---
template: project-status
template_version: 2.0.0
project_owned: true
record_contract: project-status
record_schema_version: 1
status: current
---

# Project Status

## Current state

MILESTONE-0013 is active. The `0.3.0a1` public-alpha candidate now includes completed MILESTONE-0014 through MILESTONE-0016 research governance, guidance completeness, project-agent composition, and consumer-compatibility hardening; TASK-0020 restored Poetry Core packaging and PPW-style developer bootstrap; connected package/CI evidence remains the release gate.

## Current milestone

MILESTONE-0013 — Public alpha hardening.

## Recently completed

- Completed TASK-0020: restored Poetry Core packaging, pyproject-owned versioning, and PPW-style developer bootstrap with automatic Git hook installation.

- Completed MILESTONE-0016: GetDone-style `.project-agent/` research extensions, composition locks, generalized provenance/pools/selectors, state-schema checks, agent-plan conformance, and xihbm compatibility evidence.

- Completed MILESTONE-0015: deeper diagnosis, multiple-testing/selection-bias, early-stopping, meta-model ablation/OOF guidance, adherence gates, and a sequential research walkthrough.
- Completed MILESTONE-0014: `.automo/` research governance, `automo guidance`, and bounded GetDone capability handoff.

- Removed legacy package/CLI identity and generated source-tree artifacts.
- Added versioned public persistence envelopes and one package-version source.
- Defined/tested public extension imports and security trust boundaries.
- Added fresh-project scaffolding, six synthetic onboarding examples, and controlled CLI error tests.
- Verified wheel and sdist clean installs including fresh init/validate/doctor smoke workflows.

## In progress

- Refreshing wheel/sdist clean-install evidence for the Poetry Core candidate, plus connected Python 3.11–3.13 CI and complete pre-commit execution evidence.

## Blocked

- Local complete pre-commit execution is unavailable because this environment cannot resolve/install remote hook environments from the network. Publication is intentionally gated on connected CI instead of waiving the check.

## Key decisions

- Pre-commit is the canonical repository-quality gate; it retains PPW-style repository/configuration hygiene while Ruff replaces overlapping Black/isort/Flake8-family checks. Developer Git hooks and CI consume the same configuration.
- Public examples remain synthetic and domain-neutral.
- Agent research governance, guidance completeness, project-specific extension composition, and consumer compatibility are explicit public-alpha blockers and are now locally satisfied through MILESTONE-0016.

## Project health

- 123 tests pass locally.
- Previous setuptools wheel/sdist evidence is intentionally stale after TASK-0020; current Poetry Core package build awaits connected dependency provisioning.
- GetDone 1.1.2 validates 27 managed files with 0 errors and 10 expected project-owned warnings.

## Risks

- CI may reveal lint/format or Python-version-specific issues that cannot be reproduced in this offline container.

## Remaining milestones

1. MILESTONE-0013 — complete EC-010 through EC-013, then close the milestone and publish.

## Next deterministic step

NEXT-0020 — run connected Poetry Core package/smoke, Python 3.11–3.13 CI, and the complete pre-commit gate, then record the result before publication.
