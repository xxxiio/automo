---
template: next-step
template_version: 3.0.0
project_owned: true
record_contract: next-step
record_schema_version: 1
id: NEXT-0020
status: proposed
milestone_id: MILESTONE-0013
advances_exit_criteria: [EC-010, EC-011, EC-012, EC-013]
---

# Next Deterministic Step

## Objective

Run connected CI for the corrected Poetry Core `0.3.0a1` candidate, including package/smoke, Python 3.11-3.13, and the complete pre-commit quality gate, then record the result before publication.

## Why this is next

TASK-0020 completed the Poetry packaging/bootstrap correction, but that backend change invalidated prior wheel/sdist evidence. No higher-priority feature work remains; connected package and quality evidence is now the next release gate.

## Preconditions

- Local tests/examples/wheel/sdist release gates pass.
- `.github/workflows/ci.yml` and `.pre-commit-config.yaml` are committed.

## Inputs

- `.github/workflows/ci.yml`
- `.pre-commit-config.yaml`
- `pyproject.toml`
- current `0.3.0a1` source tree

## Ordered actions

1. Build the Poetry Core wheel and sdist in the CI health job and confirm both clean-install smoke paths pass.
2. Execute tests on Python 3.11, 3.12, and 3.13.
3. Confirm the single canonical `pre-commit run --all-files --show-diff-on-failure` job passes the full PPW-derived hygiene + Ruff hook set.
4. Record CI evidence for EC-010 through EC-013.
5. Only after all four pass, mark MILESTONE-0013 complete and publish the prepared artifacts.

## Expected outputs

- Passing CI evidence or actionable failures.

## Acceptance criteria

- [ ] NS-001: Poetry Core wheel and sdist clean-install smoke passes.
- [ ] NS-002: Python 3.11–3.13 jobs pass.
- [ ] NS-003: Complete pre-commit hook execution passes.

## Validation

```bash
# Executed by connected CI:
uv sync --extra dev --python <3.11|3.12|3.13>
python -m pip install "pre-commit==4.6.0"
pre-commit run --all-files --show-diff-on-failure
uv run --python <version> pytest -q
```

## Stop conditions

- Stop publication if any CI/pre-commit job fails.

## Out of scope

- New feature development.
