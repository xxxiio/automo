# Contributing to Automo

Automo targets Python 3.11 and newer and keeps its development workflow deliberately small.

## Development setup

Install Poetry, then bootstrap the development environment and Git hook once per clone:

```bash
python scripts/init_dev.py
```

The bootstrap explicitly runs `poetry install --with dev` followed by `poetry run pre-commit install --install-hooks`. This mirrors PPW's post-generation developer setup without making normal package installation mutate Git state.

After installation, ordinary `git commit` commands run the configured pre-commit hooks automatically.

## Canonical quality gate

`.pre-commit-config.yaml` is the single source of truth for fast repository-quality checks. It includes repository/configuration hygiene plus Ruff linting and formatting. Ruff replaces overlapping Black, isort, pyupgrade, and Flake8-family responsibilities; it does not replace the non-Ruff hooks.

Run the complete local hook set explicitly before opening a pull request:

```bash
poetry run pre-commit run --all-files
poetry run pytest -q
poetry run python scripts/health_gate.py
```

Direct Ruff commands are useful only for troubleshooting individual lint/format issues. Do not maintain a separate canonical Ruff gate outside pre-commit.

## Documentation tooling

Documentation tooling is optional and non-blocking for core development:

```bash
poetry install --with docs
poetry run zensical serve
```

Keep public runtime contracts domain-neutral, add focused tests for behavior changes, and prefer small runnable examples for new extension points.
