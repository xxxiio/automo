---
template: next-step
template_version: 3.0.0
project_owned: true
record_contract: next-step
record_schema_version: 1
id: NEXT-0020
status: proposed
milestone_id: MILESTONE-0013
advances_exit_criteria: [EC-012, EC-013]
---

# Next Deterministic Step

## Objective

Run the configured connected CI matrix and complete pre-commit quality gate for the corrected `0.3.0a1` release candidate and record the result before publication.

## Why this is next

All locally executable public-alpha gates are passing; no higher-priority unfinished release work remains before CI quality evidence.

## Preconditions

- Local tests/examples/wheel/sdist release gates pass.
- `.github/workflows/ci.yml` and `.pre-commit-config.yaml` are committed.

## Inputs

- `.github/workflows/ci.yml`
- `.pre-commit-config.yaml`
- `pyproject.toml`
- current `0.3.0a1` source tree

## Ordered actions

1. Execute CI on Python 3.11, 3.12, and 3.13.
2. Confirm the single canonical `pre-commit run --all-files --show-diff-on-failure` job passes the full PPW-derived hygiene + Ruff hook set.
3. Record CI evidence for EC-012 and EC-013.
4. Only after both pass, mark MILESTONE-0013 complete and publish the prepared artifacts.

## Expected outputs

- Passing CI evidence or actionable failures.

## Acceptance criteria

- [ ] NS-001: Python 3.11–3.13 jobs pass.
- [ ] NS-002: Complete pre-commit hook execution passes.

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
