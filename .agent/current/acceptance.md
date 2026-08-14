---
template: acceptance-report
template_version: 2.0.0
project_owned: true
record_contract: acceptance-report
record_schema_version: 1
status: draft
task_id: TASK-0016
---

# Current Acceptance Report

## Task

TASK-0016 — Automo 0.3.0a1 public-alpha release candidate.

## Gate results

| Gate ID | Gate | Status | Evidence |
|---|---|---|---|
| G-001 | Source/package identity and cleanliness | pass | source check and package inspection |
| G-002 | Versioned persistence/public API | pass | public release tests |
| G-003 | Security/onboarding/release docs | pass | public docs and examples |
| G-004 | Wheel and sdist clean installs | not-run | previous setuptools artifact evidence invalidated by TASK-0020 Poetry Core migration; rebuild pending in connected CI |
| G-005 | Python 3.11–3.13 CI | not-run | configured workflow; connected CI unavailable locally |
| G-006 | Pre-commit quality gate | not-run | PPW-derived hygiene + Ruff hooks configured; offline environment cannot provision remote hook environments |
| G-007 | GetDone project contract | pass | 27 managed files, 0 errors, 10 expected warnings |

## Commands run

```bash
python -m pytest -q
python scripts/health_gate.py --keep-dist  # current Poetry Core build blocked by unavailable build dependency
uv run --with pre-commit==3.8.0 pre-commit --version  # failed: offline DNS/dependency resolution
```

## Checks not run

- Poetry Core wheel/sdist build-install smoke for the current candidate.
- Connected CI matrix and pre-commit hooks.

## Waivers

- None.

## Residual risk

- Publication remains gated on connected CI success.
