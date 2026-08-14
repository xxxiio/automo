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
- `uv` for development dependency management and canonical tool execution.
- `pip` remains sufficient for installing the built standalone package.
- No database, network service, credential, or GetDone installation is required for the standalone health gate.
- GetDone is optional and is installed only through the `getdone` extra.

## Install

```bash
python -m pip install .
```

## Development build

```bash
uv sync --extra dev
```

Documentation tooling is intentionally separate from the core development gate:

```bash
uv sync --extra docs
uv run zensical serve
# optional static build check
uv run zensical build
```

## Format

```bash
uv run --extra dev ruff format src tests scripts
```

## Lint

```bash
uv run --extra dev ruff check src tests scripts
```

Ruff is the canonical formatter/linter. In dependency-constrained offline environments where Ruff is not already cached, the standalone health gate still runs the repository-owned deterministic source-hygiene check:

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
uv run --extra dev pytest -q
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

- Ruff is run through `uv` in normal development and CI. If the current environment is offline and Ruff is not already present in the uv cache, `scripts/source_check.py` remains the dependency-free fallback for the local release health gate.
- Zensical is documentation tooling, not a release blocker. Run `uv run --extra docs zensical serve` or `uv run --extra docs zensical build` when documentation dependencies are available.
- A standalone GetDone project-validator executable is not bundled with Automo. GetDone-specific validation is available only when the optional integration package supplies it.
