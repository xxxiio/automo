---
template: next-step
template_version: 3.0.0
project_owned: true
record_contract: next-step
record_schema_version: 1
id: NEXT-0030
status: proposed
milestone_id: MILESTONE-0013
advances_exit_criteria: [EC-010, EC-011, EC-012, EC-013]
---

# Next Deterministic Step

## Objective

Run connected CI for the tox-free Poetry/pre-commit/pytest `0.3.0a1` candidate and record package plus compatibility evidence before publication.

## Why this is next

TASK-0030 removes tox and the local multi-interpreter burden. No higher-priority feature work remains; connected release evidence is the next blocker.

## Preconditions

- `python scripts/init_dev.py` completes.
- Standard `.git/hooks/pre-commit` exists and is executable.
- Local `poetry run pre-commit run --all-files --show-diff-on-failure` passes.

## Ordered actions

1. Run the connected GitHub quality job and confirm full-repository pre-commit passes.
2. Run `poetry run pytest -q` on Python 3.11, 3.12, and 3.13 through the CI matrix.
3. Build the Poetry Core wheel and sdist and confirm both clean-install smoke paths pass.
4. Record EC-010 through EC-013 evidence.
5. Close MILESTONE-0013 only after all release gates pass.

## Acceptance criteria

- [ ] NS-001: Poetry Core wheel clean-install smoke passes.
- [ ] NS-002: Poetry Core sdist clean-install smoke passes.
- [ ] NS-003: pytest passes on Python 3.11, 3.12, and 3.13 in connected CI.
- [ ] NS-004: full-repository pre-commit passes locally and in GitHub.

## Validation

```bash
python scripts/init_dev.py
poetry run pre-commit run --all-files --show-diff-on-failure
poetry run pytest -q
poetry run python scripts/health_gate.py --skip-tests
```

## Stop conditions

- Stop publication if any pre-commit/pytest/package gate fails.

## Out of scope

- Tox or tox plugins.
- Conda-specific repository configuration.
- New feature development.
