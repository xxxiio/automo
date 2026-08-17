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

The release candidate is clean, versioned, documented, and passes local source/tests after TASK-0020; uv_build wheel/sdist build-install evidence must be refreshed in connected CI because uv_build cannot be provisioned in this sandbox.

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

- [ ] AC-001: Current uv_build release candidate passes source/tests/examples/wheel/sdist gates.
- [x] AC-002: Public persistence/API/security/onboarding contracts are explicit.
- [x] AC-003: Local pre-commit runs repository hygiene, Ruff, and pytest through uv; connected CI separately runs the same pytest suite on Python 3.11, 3.12, and 3.13.
- [ ] AC-004: Connected CI confirms uv_build package/smoke, Python 3.11–3.13, and the canonical complete pre-commit quality job pass.

## Validation

```bash
python -m pytest -q
python -m compileall -q src tests scripts examples
python scripts/health_gate.py --keep-dist
PYTHONPATH=/mnt/data/getdone112_full python -m getdone.validate_project --project-root . --skills-root /mnt/data/getdone112_full --profile standard
```
