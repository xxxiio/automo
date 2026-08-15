# Contributing to Automo

Automo targets Python 3.11 and newer and keeps its development workflow deliberately small.

## Development setup

Bootstrap the development tools, Poetry environment, and Git hook once per clone:

```bash
python scripts/init_dev.py
```

Following PPW, the bootstrap uses the current Python to install `pre-commit`, runs standard `pre-commit install`, installs Poetry, and runs `poetry install --with dev`. Poetry owns the project environment; do not manually create or activate a repository `.venv` as a prerequisite. Pre-commit writes the executable clone-local hook to `.git/hooks/pre-commit`.

After bootstrap, ordinary `git commit` uses the standard PPW/pre-commit staged-file hook and always runs the pytest unit-test hook. Before pushing or releasing, run the canonical full-repository gate: `poetry run pre-commit run --all-files --show-diff-on-failure`. GitHub runs that same full-repository command.

## Canonical quality gate

`.pre-commit-config.yaml` is the single source of truth for the repository quality gate. It includes repository/configuration hygiene, Ruff linting/formatting, and unit tests. Ruff replaces overlapping Black, isort, pyupgrade, and Flake8-family responsibilities; it does not replace the non-Ruff hooks.

Unit tests are a pre-commit hook implemented through `poetry run pytest -q`. Cross-version compatibility is verified by the GitHub Python 3.11/3.12/3.13 matrix.

Run the exact full-repository gate used by GitHub Actions with:

```bash
poetry run pre-commit run --all-files --show-diff-on-failure
```

Packaging/smoke validation remains a separate release concern:

```bash
poetry run python scripts/health_gate.py --skip-tests
```

Direct Ruff commands are useful only for troubleshooting individual lint/format issues. Do not maintain a separate canonical Ruff gate outside pre-commit.

## Documentation tooling

Documentation tooling is optional and non-blocking for core development:

```bash
poetry install --with docs
poetry run zensical serve
```

Keep public runtime contracts domain-neutral, add focused tests for behavior changes, and prefer small runnable examples for new extension points.
