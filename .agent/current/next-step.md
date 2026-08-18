---
template: next-step
template_version: 3.0.0
project_owned: true
record_contract: next-step
record_schema_version: 1
id: NEXT-0035
status: proposed
milestone_id: MILESTONE-0013
advances_exit_criteria: [EC-010, EC-011, EC-012, EC-013]
---

# Next Deterministic Step

## Objective

Run connected CI with the immutable setup-uv pin and finish uv reproducibility/release evidence for MILESTONE-0013.

## Ordered actions

1. Push the TASK-0035 candidate and confirm GitHub can resolve the pinned setup-uv action.
2. Run `python scripts/init_dev.py` in a fresh connected checkout and confirm it bootstraps uv when absent.
3. Run `uv lock` and commit `uv.lock`.
4. Tighten canonical `uv sync` / `uv run` commands to locked/frozen execution and rerun the full pre-commit gate.
5. Confirm GitHub Python 3.11/3.12/3.13 pytest matrix passes.
6. Confirm `uv build` wheel/sdist and clean smoke installs pass.
7. Record EC-010 through EC-013 before closing MILESTONE-0013.

## Stop conditions

- Stop publication if setup-uv resolution, bootstrap, lock generation, pre-commit, pytest, or package smoke fails.
