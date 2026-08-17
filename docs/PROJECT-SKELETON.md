# Planned Automo Project Skeleton

This document records the implemented tooling direction established by MILESTONE-0008.

## Principles

Automo keeps packaging, tests, documentation, formatting/linting, commit hooks, CI, builds, and release checks coherent and minimal around one uv-managed development workflow.

## Runtime and packaging

- Supported Python: **3.11 and newer**.
- Central project configuration: `pyproject.toml`.
- Source layout: `src/automo/`.
- Tests: `tests/`.
- `uv_build` is the PEP 517 build backend and `uv build` is the canonical build frontend.
- Standard `[project]` metadata remains authoritative while uv manages development, testing, locking, and package builds without duplicating package metadata.
- Standards-based wheel and source distribution builds.
- Clean-install CLI smoke tests are part of the health gate.

## Quality tooling

- **pre-commit** is the canonical full-repository quality gate for developer commits and CI.
- The hook set combines repository/configuration hygiene with Python lint/format checks.
- **Ruff** replaces overlapping Black, isort, Flake8, pyupgrade, and similar Python style tooling.
- Ruff does **not** replace orthogonal hooks such as YAML/TOML/JSON validation, merge-conflict detection, line-ending/whitespace normalization, large-file checks, private-key detection, or pyproject validation.
- **pytest** is the unit-test runner. Pre-commit runs it through uv locally; GitHub runs the same pytest command on Python 3.11, 3.12, and 3.13.
- Coverage may be added through pytest-compatible coverage tooling when useful.
- Type checking is a separate concern; select a checker only when the runtime contracts justify it rather than duplicating lint responsibilities.

Normal developer setup uses the repository's uv bootstrap:

```bash
python scripts/init_dev.py
uv run pre-commit run --all-files --show-diff-on-failure
```

`scripts/init_dev.py` requires uv, runs `uv sync`, and installs the standard hook with `uv run pre-commit install`. uv manages the project environment, and pre-commit creates the executable clone-local `.git/hooks/pre-commit` hook. Normal package installation never mutates Git hooks.

## Documentation

- **Zensical** replaces MkDocs/Material for MkDocs for the documentation site.
- Documentation source remains Markdown under `docs/`.
- Zensical is optional documentation tooling; its static build is useful but is not a core package-release blocker.
- API-reference generation should be selected only if it integrates cleanly with Zensical; the public guide must not depend on generated API docs.

## Automation

- Local Git commits use standard pre-commit checks plus an always-run pytest hook. The explicit local full-repository gate and the GitHub quality job both execute `pre-commit run --all-files --show-diff-on-failure`.
- Unit tests are part of the local gate through `uv run pytest -q`. GitHub uses a Python 3.11/3.12/3.13 matrix to run the same pytest command for compatibility.
- Packaging/smoke and documentation remain separate CI jobs because they are release/artifact concerns rather than unit-test hooks.
- The dependency-light package health gate covers source hygiene, tests, package build, and clean-install smoke testing; Zensical remains optional for core development.

## Proposed repository shape

```text
automo/
├── .github/
│   └── workflows/
├── .agent/
├── docs/
├── src/
│   └── automo/
├── tests/
├── scripts/
├── pyproject.toml
├── zensical.toml
├── .pre-commit-config.yaml
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── SECURITY.md
```

## Non-goals

- Automo core must not contain validation milestones tied to any single downstream/domain package.
- Avoid redundant formatting/linting tools when Ruff covers the requirement.
- Do not make GetDone, a hosted registry, MLflow, S3, or a specific ML framework mandatory.
