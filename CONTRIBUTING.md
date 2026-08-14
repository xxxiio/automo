# Contributing to Automo

Automo targets Python 3.11 and newer and keeps its development workflow deliberately small.

## Development setup

```bash
uv sync --extra dev
uv run pre-commit install
```

## Canonical quality gate

Pre-commit is the single source of truth for source formatting and linting. Ruff runs through the configured hooks rather than through a separate hand-maintained command list.

```bash
uv run pre-commit run --all-files
uv run pytest -q
python scripts/health_gate.py
```

Direct Ruff commands are useful only for troubleshooting individual lint/format issues.

Documentation tooling is optional and non-blocking for core development:

```bash
uv sync --extra docs
uv run zensical serve
```

Keep public runtime contracts domain-neutral, add focused tests for behavior changes, and prefer small runnable examples for new extension points.
