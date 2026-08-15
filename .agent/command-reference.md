---
template: command-reference
template_version: 2.0.0
template_digest: "e4d8cbb2ae8f31215b2bee559925c4cf61753151e2dab8712969a460b7a78ef1"
project_owned: true
record_contract: command-reference
record_schema_version: 1
status: current
---

# Project Commands

## Environment prerequisites

- Python 3.11 or newer.
- Poetry for development dependency management, test execution, documentation tooling, and package builds.
- `pip` remains sufficient for installing the built standalone package.
- No database, network service, credential, or GetDone installation is required for the standalone health gate.
- GetDone is optional and is installed only through the `getdone` extra.

## Install

```bash
python -m pip install .
```

## Development build

For a normal developer clone, run the PPW-style one-command bootstrap:

```bash
python scripts/init_dev.py
```

The bootstrap runs `poetry install --with dev` and `poetry run pre-commit install --install-hooks`.

Ordinary `git commit` then runs `.pre-commit-config.yaml` automatically. The explicit full local source-quality gate is:

```bash
poetry run pre-commit run --all-files
```

Documentation tooling is intentionally separate from the core development gate:

```bash
poetry install --with docs
poetry run zensical serve
# optional static build check
poetry run zensical build
```

## Format

Formatting is owned by the Ruff formatter hook inside pre-commit. For a targeted hook run in an activated developer environment:

```bash
pre-commit run ruff-format --all-files
```

Direct `ruff format` is troubleshooting-only and is not a second canonical gate.

## Lint

Linting is owned by the Ruff lint hook inside pre-commit, while non-Ruff hooks continue to enforce repository/configuration hygiene. For a targeted hook run:

```bash
pre-commit run ruff-check --all-files
```

The complete canonical source-quality result comes only from `pre-commit run --all-files`. In dependency-constrained offline environments where hook environments are unavailable, the repository-owned deterministic source-hygiene fallback is:

```bash
python scripts/source_check.py
```

## Static analysis and type checking

```bash
python -m compileall -q src tests scripts
```

A dedicated third-party type checker is not configured for the 0.1 release boundary.

## Unit tests

```bash
poetry run pytest -q
```

The dependency-light fallback used by the release health gate is:

```bash
python -m pytest -q
```

Focused example:

```bash
python -m pytest -q tests/test_execution.py
```

## Integration and end-to-end tests

```bash
python -m pytest -q tests/test_cli.py tests/test_integration.py tests/test_release_health.py
```

## Canonical full health gate

```bash
python scripts/health_gate.py
```

The gate checks source hygiene, compilation, all tests, wheel construction, wheel contents, isolated wheel installation, CLI help, project navigation, and standalone optional-integration behaviour.

## Package and release

```bash
python scripts/health_gate.py --keep-dist
python -m pip wheel . --no-deps --no-build-isolation -w dist
```

Standalone installation smoke test:

```bash
python -m venv --system-site-packages .release-venv
.release-venv/bin/python -m pip install --no-deps dist/automo-*.whl
.release-venv/bin/python -m automo.cli --help
```

Optional GetDone integration installation:

```bash
python -m pip install ".[getdone]"
automo integration status --enabled
```

## Security and performance checks

```bash
python -m pytest -q tests/test_capabilities.py tests/test_temporal_stability.py tests/test_promotions.py
```

These tests cover protected-evidence hashes, rollback, bounded trial execution, and non-deploying promotion recommendations. Dedicated penetration and performance benchmark suites are not configured for 0.1.

## Unavailable checks

- The complete pre-commit gate requires its remote hook environments. If the current environment is offline and those environments are not already cached, `scripts/source_check.py` remains the dependency-free fallback for local source-hygiene evidence; this does not satisfy EC-013.
- Zensical is documentation tooling, not a release blocker. Run `poetry run zensical serve` or `poetry run zensical build` after installing the docs group when documentation dependencies are available.
- A standalone GetDone project-validator executable is not bundled with Automo. GetDone-specific validation is available only when the optional integration package supplies it.
