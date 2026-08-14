# Planned Automo Project Skeleton

This document records the implemented tooling direction established by MILESTONE-0008.

## Principles

Automo will borrow the comprehensive project shape of Python Project Wizard (PPW) without inheriting its older exact tool choices. The skeleton should keep packaging, tests, documentation, formatting/linting, commit hooks, CI, builds, and release checks coherent and minimal.

## Runtime and packaging

- Supported Python: **3.11 and newer**.
- Central project configuration: `pyproject.toml`.
- Source layout: `src/automo/`.
- Tests: `tests/`.
- Standards-based wheel and source distribution builds.
- Clean-install CLI smoke tests are part of the health gate.

## Quality tooling

- **pre-commit** is the canonical fast repository-quality gate for developer commits and CI.
- The hook set combines repository/configuration hygiene with Python lint/format checks.
- **Ruff** replaces overlapping Black, isort, Flake8, pyupgrade, and similar Python style tooling.
- Ruff does **not** replace orthogonal hooks such as YAML/TOML/JSON validation, merge-conflict detection, line-ending/whitespace normalization, large-file checks, private-key detection, or pyproject validation.
- **pytest** is the canonical test runner.
- Coverage may be added through pytest-compatible coverage tooling when useful.
- Type checking is a separate concern; select a checker only when the runtime contracts justify it rather than duplicating lint responsibilities.

Normal developer setup and quality commands use the activated project environment:

```bash
uv sync --extra dev
source .venv/bin/activate
pre-commit install
pre-commit run --all-files
pytest -q
```

Agent/sandbox execution may use `uv run --extra dev pre-commit run --all-files` when shell activation is not persistent. Direct Ruff commands are troubleshooting tools, not a second canonical quality gate.

## Documentation

- **Zensical** replaces MkDocs/Material for MkDocs for the documentation site.
- Documentation source remains Markdown under `docs/`.
- Zensical is optional documentation tooling; its static build is useful but is not a core package-release blocker.
- API-reference generation should be selected only if it integrates cleanly with Zensical; the public guide must not depend on generated API docs.

## Automation

- Local Git commits and GitHub Actions both execute the same `.pre-commit-config.yaml`; developers install the Git hook, while CI invokes pre-commit directly.
- GitHub Actions keeps pre-commit quality, the Python-version pytest matrix, packaging/smoke checks, and documentation builds as separate jobs.
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
