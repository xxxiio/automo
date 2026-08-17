from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import automo
from automo.cli import app
from automo.refresh import ModelPoolSnapshot
from automo.refresh.pool import FilesystemPoolStore
from automo.registry import FilesystemModelRegistry, TrainingProvenance
from automo.research import (
    CandidateProposal,
    InterventionKind,
    ResearchBudget,
    ResearchIntervention,
    ResearchPlan,
    ResearchSafeguards,
    ResearchSearchSpace,
)
from automo.research.store import FilesystemResearchStore

RUNNER = CliRunner()


def test_public_root_api_contains_documented_extension_contracts() -> None:
    names = {
        "DataSource",
        "DataSnapshot",
        "FeatureSpec",
        "FeatureSetSpec",
        "FeatureComputer",
        "ObjectiveSpec",
        "MetricSpec",
        "EvaluationContext",
        "Evaluator",
        "ModelSpec",
        "ModelTrainer",
        "TrainingRequest",
        "TrainingResult",
        "ModelGraphSpec",
        "ModelNodeSpec",
        "ModelOutputInput",
        "CrossFitSpec",
        "ResearchPlugin",
        "ResearchRuntime",
    }
    assert names <= set(automo.__all__)


def test_init_creates_valid_minimal_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    assert RUNNER.invoke(app, ["init", "--root", str(project)]).exit_code == 0
    result = RUNNER.invoke(app, ["validate", "--root", str(project)])
    assert result.exit_code == 0, result.output
    doctor = RUNNER.invoke(app, ["doctor", "--root", str(project)])
    assert doctor.exit_code == 0, doctor.output
    assert "Project plugin" in doctor.output


def test_registry_documents_are_versioned(tmp_path: Path) -> None:
    class Codec:
        id = "test.codec"

        def save(self, model, path: Path) -> None:
            path.write_text(str(model), encoding="utf-8")

        def load(self, path: Path):
            return path.read_text(encoding="utf-8")

    codec = Codec()
    registry = FilesystemModelRegistry(tmp_path / "registry", codecs=(codec,))
    provenance = TrainingProvenance(
        data_source_id="data",
        data_snapshot_id="snapshot",
        data_snapshot_hash="abc",
        feature_set_id="features",
        model_spec_id="model",
        objective_id="objective",
        runner_implementation="linear.single_feature",
        python_version="3.11",
    )
    manifest = registry.register_model(
        "model-artifact",
        implementation="linear.single_feature",
        model_spec_id="model",
        objective_id="objective",
        feature_set_id="features",
        provenance=provenance,
        codec=codec,
    )
    raw = __import__("yaml").safe_load(
        (registry.models_root / manifest.id / "manifest.yaml").read_text(encoding="utf-8")
    )
    assert raw["artifact_type"] == "automo.model_manifest"
    assert raw["schema_version"] == 1


def test_research_and_pool_documents_are_versioned(tmp_path: Path) -> None:
    store = FilesystemResearchStore(tmp_path / "research")
    proposal = CandidateProposal(
        id="CANDIDATE-0001",
        baseline_model_spec_id="baseline",
        intervention=ResearchIntervention(InterventionKind.MODEL, {"model_spec_id": "candidate"}),
        rationale=("test",),
        expected_effect="improve",
        falsification=("does not improve",),
        priority=1,
    )
    plan = ResearchPlan(
        id="RESEARCH-0001",
        baseline_model_spec_id="baseline",
        data_source_id="data",
        split_strategy_id="split",
        diagnosis="underfitting",
        findings=(),
        search_space=ResearchSearchSpace("space", model_spec_ids=("candidate",)),
        budget=ResearchBudget(),
        safeguards=ResearchSafeguards(),
        candidates=(proposal,),
    )
    plan_path = store.create_plan(plan)
    raw_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert raw_plan["artifact_type"] == "automo.research_plan"
    assert raw_plan["schema_version"] == 1

    pool_store = FilesystemPoolStore(tmp_path / "pools")
    snapshot_path = pool_store.save_snapshot(ModelPoolSnapshot("pool", "iteration", (), ()))
    raw_pool = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert raw_pool["artifact_type"] == "automo.model_pool_snapshot"
    assert raw_pool["schema_version"] == 1


def test_common_missing_ids_are_controlled_cli_errors() -> None:
    for args in (
        ["models", "show", "MODEL-999999", "--root", "."],
        ["refresh", "show", "NOPE", "--root", "."],
        ["research", "show", "NOPE", "--root", "."],
    ):
        result = RUNNER.invoke(app, args)
        assert result.exit_code == 1
        assert "Error:" in result.stderr
        assert "Traceback" not in result.stderr


def test_release_workflow_is_tag_only_and_reuses_successful_ci() -> None:
    workflow = Path(".github/workflows/publish-pypi.yml").read_text(encoding="utf-8")
    assert "push:" in workflow
    assert "tags:" in workflow
    assert '"v*"' in workflow
    assert "release:" not in workflow
    assert "environment:\n      name: pypi" in workflow
    assert "id-token: write" in workflow
    assert "Verify tag points to main HEAD" in workflow
    assert "origin/main" in workflow
    assert "GITHUB_REF_NAME" in workflow
    assert "Require successful CI for tagged main commit" in workflow
    assert "workflow_id: 'ci.yml'" in workflow
    assert "status: 'success'" in workflow
    assert "head_sha: sha" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "PYPI_TOKEN" not in workflow
    assert "pre-commit run --all-files" not in workflow
    assert "pytest -q" not in workflow
    assert "does not match package version" in workflow
    assert "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9 # v9.0.0" in workflow
    assert "uv sync" in workflow
    assert "uv build" in workflow
    assert "uvx twine check dist/*" in workflow
    assert "poetry" not in workflow.lower()


def test_ci_owns_quality_tests_health_docs_and_pages_without_tag_duplication() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "branches: [main]" in workflow
    assert "tags:" not in workflow
    assert workflow.count("pre-commit run --all-files") == 1
    assert "name: full quality gate" in workflow
    assert 'python-version: ["3.11", "3.12", "3.13"]' in workflow
    assert "matrix.python-version" in workflow
    assert "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9 # v9.0.0" in workflow
    assert "enable-cache: true" in workflow
    assert "uv sync" in workflow
    assert "uv run pytest -q" in workflow
    assert "uv run pre-commit run --all-files --show-diff-on-failure" in workflow
    assert "poetry" not in workflow.lower()
    assert "tox" not in workflow.lower()
    assert "scripts/health_gate.py --skip-tests" in workflow
    assert "zensical build --clean --strict" in workflow
    assert "actions/configure-pages@v5" in workflow
    assert "actions/upload-pages-artifact@v4" in workflow
    assert "actions/deploy-pages@v4" in workflow
    assert "name: github-pages" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert not Path(".github/workflows/docs.yml").exists()


def test_precommit_combines_repository_hygiene_with_ruff_without_legacy_overlap() -> None:
    import yaml

    config = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")
    parsed = yaml.safe_load(config)
    assert isinstance(parsed, dict)
    assert isinstance(parsed.get("repos"), list)
    for hook in (
        "check-added-large-files",
        "check-ast",
        "check-case-conflict",
        "check-json",
        "check-merge-conflict",
        "check-toml",
        "check-yaml",
        "debug-statements",
        "detect-private-key",
        "end-of-file-fixer",
        "mixed-line-ending",
        "trailing-whitespace",
        "validate-pyproject",
        "ruff-check",
        "ruff-format",
        "pytest-tests",
    ):
        assert f"id: {hook}" in config
    ruff_repo = next(
        repo
        for repo in parsed["repos"]
        if repo["repo"] == "https://github.com/astral-sh/ruff-pre-commit"
    )
    ruff_check = next(hook for hook in ruff_repo["hooks"] if hook["id"] == "ruff-check")
    assert ruff_check["args"] == ["--fix", "--exit-non-zero-on-fix", "."]
    assert ruff_check["pass_filenames"] is False
    assert ruff_check["always_run"] is True
    ruff_format = next(hook for hook in ruff_repo["hooks"] if hook["id"] == "ruff-format")
    assert ruff_format["args"] == ["."]
    assert ruff_format["pass_filenames"] is False
    assert ruff_format["always_run"] is True
    local_repo = next(repo for repo in parsed["repos"] if repo["repo"] == "local")
    pytest_hook = next(hook for hook in local_repo["hooks"] if hook["id"] == "pytest-tests")
    assert pytest_hook["name"] == "unit tests"
    assert pytest_hook["entry"] == "uv run pytest -q"
    assert pytest_hook["language"] == "system"
    assert pytest_hook["pass_filenames"] is False
    assert pytest_hook["always_run"] is True
    for legacy in ("mirrors-isort", "ambv/black", "psf/black", "pycqa/flake8", "pyupgrade"):
        assert legacy not in config.lower()


def test_developer_workflow_is_uv_only() -> None:
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    project_skeleton = Path("docs/PROJECT-SKELETON.md").read_text(encoding="utf-8")
    for text in (contributing, readme, project_skeleton):
        assert "python scripts/init_dev.py" in text
        assert "uv run" in text
        assert "poetry run" not in text.lower()
        assert "poetry install" not in text.lower()
    assert "uv run pre-commit run --all-files" in contributing
    assert "uv run pytest -q" in contributing
    assert "Python 3.11" in contributing


def test_uv_build_is_the_only_build_backend_and_pyproject_owns_version() -> None:
    import tomllib

    raw = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert raw["build-system"]["build-backend"] == "uv_build"
    assert raw["build-system"]["requires"] == ["uv_build>=0.12.0,<0.13"]
    assert raw["project"]["version"] == automo.__version__
    assert "dev" in raw["dependency-groups"]
    assert "docs" in raw["dependency-groups"]
    text = Path("pyproject.toml").read_text(encoding="utf-8").lower()
    assert "poetry" not in text
    assert "tool.setuptools" not in text
    assert "setuptools.build_meta" not in text


def test_developer_bootstrap_is_uv_only_and_installs_git_hook() -> None:
    bootstrap = Path("scripts/init_dev.py").read_text(encoding="utf-8")
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "from automo" not in bootstrap
    assert "import yaml" not in bootstrap
    assert 'shutil.which("uv")' in bootstrap
    assert '[sys.executable, "-m", "pip", "install", "uv"]' in bootstrap
    assert '[sys.executable, "-m", "uv"]' in bootstrap
    assert '"sync"' in bootstrap
    assert '"pre-commit", "install"' in bootstrap
    assert "poetry" not in bootstrap.lower()
    assert "core.hooksPath" not in contributing
    assert "git config core.hooksPath .githooks" not in bootstrap
    assert "hooks/pre-commit" in bootstrap
    assert "os.X_OK" in bootstrap
    assert "python scripts/init_dev.py" in contributing
    assert "python scripts/init_dev.py" in readme
    assert ".git/hooks/pre-commit" in contributing
    assert not Path(".githooks").exists()


def test_pytest_is_local_precommit_test_gate_and_ci_owns_version_matrix() -> None:
    assert not Path("tox.ini").exists()
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "tox" not in pyproject.lower()
    import yaml

    parsed = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))
    local_repo = next(repo for repo in parsed["repos"] if repo["repo"] == "local")
    pytest_hook = next(hook for hook in local_repo["hooks"] if hook["id"] == "pytest-tests")
    assert pytest_hook["entry"] == "uv run pytest -q"
    assert pytest_hook["pass_filenames"] is False
    assert pytest_hook["always_run"] is True
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert 'python-version: ["3.11", "3.12", "3.13"]' in workflow
    assert "python-version: ${{ matrix.python-version }}" in workflow
    assert "uv run pytest -q" in workflow
    assert "poetry" not in workflow.lower()
    assert "tox" not in workflow.lower()
