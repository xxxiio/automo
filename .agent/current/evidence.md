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
| AC-001 | pass | 104-test suite, clean Git checkout simulation, and offline wheel/sdist health gate |
| AC-002 | pass | persistence/API/security/onboarding files and tests |
| AC-003 | pass | `.github/workflows/ci.yml` executes pre-commit once and tests 3.11/3.12/3.13 separately |
| AC-004 | not-run | prior connected CI run failed because `tests/fixtures/runs` was ignored and editable-install metadata tripped source hygiene; fixes are locally verified and require a connected rerun |

## Quality gate evidence

| Gate | Status | Command or artefact | Result |
|---|---|---|---|
| Tests | pass | `python -m pytest -q` | 104 passed on Python 3.13 |
| Compilation | pass | `python -m compileall -q src tests scripts examples` | passed |
| Wheel/sdist | pass | `python scripts/health_gate.py --keep-dist` | both clean-install smoke paths passed |
| Pre-commit/Ruff | not-run | `.pre-commit-config.yaml` / CI | local dependency provisioning blocked by offline DNS |
| Clean Git simulation | pass | initialize Git, `git add -A`, create ignored `src/automo.egg-info`, run source check and pytest | 20 fixture files tracked, root `runs/` ignored, source-check passed, 104 tests passed |
| GetDone 1.1.2 | pass | validator command | 27 managed files, 0 errors, 10 expected warnings |

## Checks not run

- Connected GitHub Actions rerun on the corrected commit. The previous run exposed release-candidate source-boundary bugs now fixed locally.

## Waivers

- None.

## Residual risk

- Release must not be published until connected CI provides passing EC-012/EC-013 evidence.
