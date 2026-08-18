from pathlib import Path

from typer.testing import CliRunner

from automo.cli import app

ROOT = Path(__file__).parents[1]
FIXTURE_RUNS = ROOT / "tests/fixtures/runs"
RUNNER = CliRunner()


def test_next_command() -> None:
    result = RUNNER.invoke(app, ["next", "--root", str(ROOT)])
    assert result.exit_code == 0
    assert "EXPERIMENT-0002" in result.stdout
    assert "Why next:" in result.stdout


def test_validation_reports_blocked_data() -> None:
    result = RUNNER.invoke(
        app,
        ["validate-experiment", "EXPERIMENT-0002", "--root", str(ROOT)],
    )
    assert result.exit_code == 2
    assert "unavailable-data-source" in result.stdout
    assert "User action:" in result.stdout


def test_run_experiment_command(tmp_path: Path) -> None:
    import shutil

    project = tmp_path / "project"
    shutil.copytree(ROOT / "research", project / "research")
    shutil.copytree(ROOT / "data", project / "data")
    result = RUNNER.invoke(
        app,
        [
            "run-experiment",
            "EXPERIMENT-0001",
            "--root",
            str(project),
            "--run-id",
            "cli-test-run",
        ],
    )
    assert result.exit_code == 0
    assert "Out of sample:" in result.stdout


def test_decide_command(tmp_path: Path) -> None:
    import json
    import shutil

    project = tmp_path / "project"
    shutil.copytree(ROOT / "research", project / "research")
    shutil.copytree(FIXTURE_RUNS / "experiment-0003-decision", project / "runs/decision-cli")
    decision_path = project / "runs/decision-cli/decision.json"
    decision_path.unlink()
    manifest_path = project / "runs/decision-cli/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["run_id"] = "decision-cli"
    manifest_path.write_text(json.dumps(manifest))
    result = RUNNER.invoke(app, ["decide", "decision-cli", "--root", str(project)])
    assert result.exit_code == 0
    assert "Outcome: accepted" in result.stdout
    assert decision_path.exists()


def test_run_temporal_stability_cli(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "research/experiments").mkdir(parents=True)
    (project / "data").mkdir()
    (project / "research/experiments/EXPERIMENT-0002.yaml").write_bytes(
        (ROOT / "research/experiments/EXPERIMENT-0002.yaml").read_bytes()
    )
    (project / "data/local-fixture.csv").write_bytes((ROOT / "data/local-fixture.csv").read_bytes())
    result = RUNNER.invoke(
        app,
        [
            "run-temporal-stability",
            "EXPERIMENT-0002",
            "--root",
            str(project),
            "--run-id",
            "cli-stability",
        ],
    )
    assert result.exit_code == 0
    assert "Folds executed: 3" in result.stdout
    assert (project / "runs/cli-stability/temporal-stability.json").exists()


def test_recommend_promotion_cli(tmp_path):
    import shutil

    from typer.testing import CliRunner

    from automo.cli import app

    root = tmp_path / "project"
    source = Path(__file__).parents[1]
    shutil.copytree(
        source,
        root,
        ignore=shutil.ignore_patterns(
            ".pytest_cache", "__pycache__", "recommendations", "build", "dist", "*.egg-info"
        ),
    )
    shutil.copytree(source / "tests/fixtures/runs", root / "runs")
    result = CliRunner().invoke(app, ["recommend-promotion", "--root", str(root)])
    assert result.exit_code == 0
    assert "promote-challenger" in result.stdout


def test_unified_help_exposes_project_commands() -> None:
    result = RUNNER.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("init", "doctor", "status", "plan", "run", "validate", "experiment"):
        assert command in result.stdout


def test_version_option() -> None:
    result = RUNNER.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip()


def test_status_command_and_json() -> None:
    text = RUNNER.invoke(app, ["status", "--root", str(ROOT)])
    assert text.exit_code == 0
    assert "EXPERIMENT-0002" in text.stdout
    assert "Next deterministic step" in text.stdout
    machine = RUNNER.invoke(app, ["status", "--root", str(ROOT), "--json"])
    assert machine.exit_code == 0
    payload = __import__("json").loads(machine.stdout)
    assert payload["experiment"]["id"] == "EXPERIMENT-0002"


def test_plan_command_contains_governance_fields() -> None:
    result = RUNNER.invoke(app, ["plan", "--root", str(ROOT)])
    assert result.exit_code == 0
    assert "Why next:" in result.stdout
    assert "Falsified when:" in result.stdout
    assert "Maximum trials: 3" in result.stdout


def test_doctor_requires_current_automo_project_state(tmp_path: Path) -> None:
    project = tmp_path / "project"
    init = RUNNER.invoke(app, ["init", "--root", str(project)])
    assert init.exit_code == 0, init.output
    result = RUNNER.invoke(app, ["doctor", "--root", str(project)])
    assert result.exit_code == 0, result.output
    assert "Research governance" in result.stdout
    assert "GetDone integration" in result.stdout


def test_init_preserves_existing_project_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "research/objectives").mkdir(parents=True)
    existing = project / "research/objectives/current.yaml"
    existing.write_text("sentinel: true\n")
    result = RUNNER.invoke(app, ["init", "--root", str(project)])
    assert result.exit_code == 0
    assert existing.read_text() == "sentinel: true\n"
    assert (project / "automo.toml").is_file()
    assert (project / "automo_project.py").is_file()


def test_structured_advanced_aliases_remain_available() -> None:
    result = RUNNER.invoke(app, ["experiment", "next", "--root", str(ROOT)])
    assert result.exit_code == 0
    assert "EXPERIMENT-0002" in result.stdout


def test_run_executes_exactly_one_temporal_transition(tmp_path: Path) -> None:
    import shutil

    project = tmp_path / "project"
    shutil.copytree(ROOT / "research", project / "research")
    shutil.copytree(ROOT / "data", project / "data")
    result = RUNNER.invoke(
        app,
        ["run", "--root", str(project), "--run-id", "unified-run"],
    )
    assert result.exit_code == 0
    assert "Stage: temporal-stability" in result.stdout
    assert "exactly one transition executed" in result.stdout
    assert (project / "runs/unified-run/temporal-stability.json").is_file()
    second = RUNNER.invoke(app, ["run", "--root", str(project)])
    assert second.exit_code == 1
    assert "already complete" in second.stderr
