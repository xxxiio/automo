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

- **Ruff** is the canonical formatter, import sorter, linter, upgrade/style checker, and first-line static quality tool.
- Do not add Black, isort, Flake8, pyupgrade, autoflake, or overlapping style tools unless a concrete unsupported requirement appears.
- **pytest** is the canonical test runner.
- Coverage may be added through pytest-compatible coverage tooling when useful.
- Type checking is a separate concern; select a checker only when the runtime contracts justify it rather than duplicating lint responsibilities.

Canonical commands use uv for tool execution:

```bash
uv run --extra dev ruff format --check .
uv run --extra dev ruff check .
uv run --extra dev pytest -q
```

## Documentation

- **Zensical** replaces MkDocs/Material for MkDocs for the documentation site.
- Documentation source remains Markdown under `docs/`.
- Zensical is optional documentation tooling; its static build is useful but is not a core package-release blocker.
- API-reference generation should be selected only if it integrates cleanly with Zensical; the public guide must not depend on generated API docs.

## Automation

- pre-commit runs Ruff hooks equivalent to the canonical local Ruff commands.
- GitHub Actions provisions uv and runs the same Ruff and pytest commands rather than maintaining a divergent CI-only toolchain.
- The dependency-light package health gate covers source hygiene, tests, package build, and clean-install smoke testing; Ruff is enforced through uv in normal development/CI, while Zensical remains optional.

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
