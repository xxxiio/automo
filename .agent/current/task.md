---
template: current-task
template_version: 2.0.0
project_owned: true
record_contract: current-task
record_schema_version: 1
id: TASK-0016
status: active
milestone_id: MILESTONE-0013
---

# Current Task

## Objective

Prepare and verify the Automo `0.3.0a1` public-alpha release candidate, leaving only externally executed CI/pre-commit gates if the local environment cannot provision them.

## Current behaviour

The release candidate is clean, versioned, documented, and passes local tests/build/install gates; connected CI execution remains unevidenced locally.

## Desired behaviour

All fourteen public-alpha exit criteria have reproducible evidence before publication.

## Scope

- Public release hardening only.

## Out of scope

- New model-research functionality.

## Dependencies

- MILESTONE-0012 completed.

## Risks

- Offline environment prevents installation/execution of remote pre-commit hook environments.

## Acceptance criteria

- [x] AC-001: Local source/tests/examples/wheel/sdist gates pass.
- [x] AC-002: Public persistence/API/security/onboarding contracts are explicit.
- [x] AC-003: CI configuration runs the complete pre-commit configuration once as the canonical quality gate and tests Python 3.11–3.13 separately; developer Git hooks use the same configuration.
- [ ] AC-004: Connected CI confirms the Python 3.11–3.13 test matrix and the canonical complete pre-commit quality job pass.

## Validation

```bash
python -m pytest -q
python -m compileall -q src tests scripts examples
python scripts/health_gate.py --keep-dist
PYTHONPATH=/mnt/data/getdone112_full python -m getdone.validate_project --project-root . --skills-root /mnt/data/getdone112_full --profile standard
```
