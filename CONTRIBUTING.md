# Contributing to Automo

Automo targets Python 3.11 and newer and keeps its development workflow deliberately small.

## Development setup

Bootstrap the development environment and Git hook once per clone:

```bash
python scripts/init_dev.py
source .venv/bin/activate
```

The bootstrap explicitly runs `uv sync --extra dev` followed by the clone-local `pre-commit install --install-hooks`. This mirrors PPW's post-generation developer setup without making normal package installation mutate Git state.

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1` instead.

After installation, ordinary `git commit` commands run the configured pre-commit hooks automatically.

## Canonical quality gate

`.pre-commit-config.yaml` is the single source of truth for fast repository-quality checks. It includes repository/configuration hygiene plus Ruff linting and formatting. Ruff replaces overlapping Black, isort, pyupgrade, and Flake8-family responsibilities; it does not replace the non-Ruff hooks.

Run the complete local hook set explicitly before opening a pull request:

```bash
pre-commit run --all-files
pytest -q
python scripts/health_gate.py
```

Direct Ruff commands are useful only for troubleshooting individual lint/format issues. Do not maintain a separate canonical Ruff gate outside pre-commit.

## ChatGPT and sandbox execution

Agent/sandbox environments may not keep an activated shell between commands. In that environment, the equivalent project-managed invocation is:

```bash
uv run --extra dev pre-commit run --all-files
```

That `uv run` form is an agent/sandbox convenience, not the normal developer workflow.

Documentation tooling is optional and non-blocking for core development:

```bash
uv sync --extra docs
uv run zensical serve
```

Keep public runtime contracts domain-neutral, add focused tests for behavior changes, and prefer small runnable examples for new extension points.
