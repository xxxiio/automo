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
| AC-001 | not-run | 127-test suite/source checks pass, but Poetry Core wheel/sdist evidence is stale until the current backend is built in connected CI |
| AC-002 | pass | persistence/API/security/onboarding files and tests |
| AC-003 | pass | `.github/workflows/ci.yml` executes the complete pre-commit configuration once and tests 3.11/3.12/3.13 separately; `scripts/init_dev.py` performs PPW-style Poetry development installation plus clone-local hook installation; current user/developer and GitHub workflows are Poetry-only |
| AC-004 | not-run | connected rerun must prove Poetry Core package/smoke, Python 3.11–3.13, and complete pre-commit on the corrected candidate |

## Quality gate evidence

| Gate | Status | Command or artefact | Result |
|---|---|---|---|
| Tests | pass | `PYTHONPATH=src python -m pytest -q` | 127 passed |
| Compilation | pass | `python -m compileall -q src tests scripts examples` | passed |
| Wheel/sdist | not-run | `python scripts/health_gate.py --keep-dist` | current Poetry Core backend cannot be provisioned in the offline sandbox; previous setuptools artifacts are not accepted as evidence |
| Release health | not-run | `python scripts/health_gate.py --skip-tests --keep-dist` | build phase awaits Poetry Core/build dependencies in connected CI; source/tests/compile portions pass locally |
| Pre-commit quality gate | not-run | `.pre-commit-config.yaml` / CI | PPW-derived hygiene + Ruff configuration is locally inspected/tested; remote hook environments cannot be provisioned offline |
| Clean Git simulation | pass | initialize Git, `git add -A`, create ignored `src/automo.egg-info`, run source check and pytest | 20 fixture files tracked, root `runs/` ignored, source-check passed, compatibility regression remains covered |
| GetDone 1.1.2 | pass | validator command | 27 managed files, 0 errors, 10 expected warnings |

## Checks not run

- Poetry Core wheel/sdist build-install smoke for the current backend.
- Connected GitHub Actions rerun on the corrected commit.

## Waivers

- None.

## Residual risk

- Release must not be published until connected CI refreshes EC-010/EC-011 package evidence and provides passing EC-012/EC-013 evidence.
