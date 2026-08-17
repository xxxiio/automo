---
template: next-step
template_version: 3.0.0
project_owned: true
record_contract: next-step
record_schema_version: 1
id: NEXT-0034
status: proposed
milestone_id: MILESTONE-0013
advances_exit_criteria: [EC-010, EC-011, EC-012, EC-013]
---

# Next Deterministic Step

## Objective

Finish connected uv reproducibility and release evidence for MILESTONE-0013.

## Ordered actions

1. Run `python scripts/init_dev.py` in a fresh connected checkout and confirm it bootstraps uv when absent.
2. Run `uv lock` and commit `uv.lock`.
3. Tighten canonical `uv sync` / `uv run` commands to `--locked` and rerun the full pre-commit gate.
4. Confirm GitHub Python 3.11/3.12/3.13 pytest matrix passes.
5. Confirm `uv build` wheel/sdist and clean smoke installs pass.
6. Record EC-010 through EC-013 before closing MILESTONE-0013.

## Stop conditions

- Stop publication if bootstrap, lock generation, pre-commit, pytest, or package smoke fails.
