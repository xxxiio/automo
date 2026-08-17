---
template: project-status
template_version: 2.0.0
project_owned: true
record_contract: project-status
record_schema_version: 1
status: current
---

# Project Status

## Current state

MILESTONE-0013 is active. Automo `0.3.0a1` now uses uv as the single canonical development/environment/build workflow. TASK-0033 removed the active Poetry CLI/Core contract, moved development/documentation dependencies to standardized dependency groups, switched packaging to `uv_build`, and switched local/CI/release execution to uv.

## Current milestone

MILESTONE-0013 — Public alpha hardening.

## Recently completed

- Completed TASK-0033: uv-only developer, CI, documentation, health, and package-build workflow.
- Completed TASK-0032: full-repository Ruff auto-fix scope aligned between local pre-commit and CI.
- Completed TASK-0030: tox removed; pytest is the direct unit-test gate.
- Completed MILESTONE-0014 through MILESTONE-0016 research governance/guidance/compatibility work.

## In progress

- Generate and commit `uv.lock` in a connected checkout, then tighten canonical sync/run commands to `--locked`.
- Refresh connected wheel/sdist, smoke, full pre-commit, and Python 3.11/3.12/3.13 evidence.

## Blocked

- This execution sandbox cannot resolve PyPI, so `uv lock`, dependency-backed `uv build`, Ruff, and complete pre-commit cannot be executed here.

## Key decisions

- uv owns the project environment, dependency resolution, Python selection, command execution, and build frontend.
- `uv_build` is the PEP 517 build backend.
- Pre-commit remains the repository-quality orchestrator; its pytest hook executes `uv run pytest -q`.
- GitHub uses `astral-sh/setup-uv` and retains explicit Python 3.11/3.12/3.13 compatibility jobs.
- No tox or Poetry layer remains in the active workflow.

## Project health

- Local pytest: 132 passed on the available interpreter after TASK-0033.
- `compileall`: passed.
- `scripts/source_check.py`: passed.
- Connected uv lock/build/pre-commit and cross-version evidence remain pending.

## Remaining milestones

1. MILESTONE-0013 — complete EC-010 through EC-013, then close the milestone and publish.

## Next deterministic step

NEXT-0033 — generate/commit `uv.lock` in a connected checkout, tighten gates to `--locked`, then run the complete connected release evidence sequence.
