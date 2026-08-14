---
template: evidence-manifest
template_version: 2.0.0
project_owned: true
record_contract: evidence-manifest
record_schema_version: 1
status: draft
task_id: TASK-0016
---

# Current Evidence Manifest

## Task

TASK-0016 — Prepare and verify the Automo 0.3.0a1 public-alpha release candidate.

## Acceptance evidence

| Criterion ID | Status | Evidence |
|---|---|---|
| AC-001 | pass | 93-test suite and offline wheel/sdist health gate |
| AC-002 | pass | persistence/API/security/onboarding files and tests |
| AC-003 | pass | `.github/workflows/ci.yml` executes pre-commit once and tests 3.11/3.12/3.13 separately |
| AC-004 | not-run | connected CI is unavailable from this environment |

## Quality gate evidence

| Gate | Status | Command or artefact | Result |
|---|---|---|---|
| Tests | pass | `python -m pytest -q` | 93 passed |
| Compilation | pass | `python -m compileall -q src tests scripts examples` | passed |
| Wheel/sdist | pass | `python scripts/health_gate.py --keep-dist` | both clean-install smoke paths passed |
| Pre-commit/Ruff | not-run | `.pre-commit-config.yaml` / CI | local dependency provisioning blocked by offline DNS |
| GetDone 1.1.2 | pass | validator command | 27 managed files, 0 errors, 10 expected warnings |

## Checks not run

- Connected GitHub Actions Python 3.11–3.13 test matrix and pre-commit/Ruff quality job; this environment cannot access PyPI/GitHub to provision hook dependencies.

## Waivers

- None.

## Residual risk

- Release must not be published until connected CI provides passing EC-012/EC-013 evidence.
