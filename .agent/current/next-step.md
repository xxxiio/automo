---
template: next-step
template_version: 3.0.0
project_owned: true
record_contract: next-step
record_schema_version: 1
id: NEXT-0032
status: proposed
milestone_id: MILESTONE-0013
advances_exit_criteria: [EC-010, EC-011, EC-012, EC-013]
---

# Next Deterministic Step

## Objective

Run the corrected full-repository pre-commit gate in a connected development environment and then record the remaining package/CI evidence.

## Ordered actions

1. Run `poetry run pre-commit run --all-files --show-diff-on-failure` and confirm Ruff plus pytest pass.
2. Commit any auto-format changes if Ruff makes them, then rerun until clean.
3. Run connected Python 3.11/3.12/3.13 pytest CI.
4. Run wheel and sdist clean-install smoke tests.
5. Record EC-010 through EC-013 evidence before closing MILESTONE-0013.

## Stop conditions

- Stop publication if any pre-commit, pytest, or package gate fails.
