from pathlib import Path

from typer.testing import CliRunner

from automo.cli import app
from automo.governance import MilestoneOutcome, MilestoneStatus, ResearchGovernance
from automo.guidance import select_guidance
from automo.ux import initialise_mr_project, validate_project

RUNNER = CliRunner()


def test_init_creates_automo_research_governance(tmp_path: Path) -> None:
    initialise_mr_project(tmp_path)
    assert (tmp_path / ".automo/project.yaml").is_file()
    assert (tmp_path / ".automo/roadmap.yaml").is_file()
    assert (tmp_path / ".automo/current/next-step.yaml").is_file()
    ok, errors, _ = validate_project(tmp_path)
    assert ok, errors


def test_milestone_lifecycle_and_plan_mode(tmp_path: Path) -> None:
    governance = ResearchGovernance(tmp_path)
    governance.initialise()
    item = governance.create_milestone(
        "R001", question="Does the intervention improve the objective?",
        why_next="Current evidence leaves this as the highest-value unresolved question.",
        exit_criteria=("candidate evaluated", "conclusion recorded"),
    )
    assert item.status == MilestoneStatus.PROPOSED
    assert governance.current_milestone().id == "R001"
    for target in (MilestoneStatus.PLANNING, MilestoneStatus.APPROVED, MilestoneStatus.ACTIVE):
        item = governance.transition("R001", target)
    assert governance.require_execution_ready().id == "R001"
    done = governance.conclude("R001", outcome=MilestoneOutcome.REJECTED, conclusion="No material improvement.")
    assert done.outcome == MilestoneOutcome.REJECTED
    assert governance.current_milestone() is None


def test_plan_mode_blocks_research_execution(tmp_path: Path) -> None:
    governance = ResearchGovernance(tmp_path)
    governance.initialise()
    try:
        governance.require_execution_ready()
    except Exception as exc:
        assert "plan mode" in str(exc)
    else:
        raise AssertionError("plan mode must block research execution")


def test_guidance_is_minimal_and_task_specific() -> None:
    docs = select_guidance("meta-model-research")
    paths = {item.path for item in docs}
    assert "workflows/research-iteration.md" in paths
    assert "workflows/meta-model-research.md" in paths
    assert "standards/leakage.md" in paths
    assert "references/meta-model-patterns.md" in paths
    assert "workflows/calibration-research.md" not in paths


def test_guidance_cli_paths_only() -> None:
    result = RUNNER.invoke(app, ["guidance", "--task-class", "experiment-design", "--paths-only"])
    assert result.exit_code == 0, result.output
    assert "workflows/experiment-design.md" in result.output
    assert "policies/sealed-oos.md" in result.output


def test_milestone_cli_flow(tmp_path: Path) -> None:
    initialise_mr_project(tmp_path)
    result = RUNNER.invoke(app, [
        "research", "milestone-create", "R001", "--question", "Does A improve B?",
        "--why-next", "It is the highest priority unresolved question.",
        "--exit-criterion", "evaluate candidate", "--root", str(tmp_path),
    ])
    assert result.exit_code == 0, result.output
    for state in ("planning", "approved", "active"):
        result = RUNNER.invoke(app, ["research", "milestone-transition", "R001", "--status", state, "--root", str(tmp_path)])
        assert result.exit_code == 0, result.output
    result = RUNNER.invoke(app, [
        "research", "milestone-conclude", "R001", "--outcome", "inconclusive",
        "--conclusion", "Evidence was insufficient.", "--root", str(tmp_path),
    ])
    assert result.exit_code == 0, result.output


def test_getdone_handoff_stays_in_automo_state(tmp_path: Path) -> None:
    initialise_mr_project(tmp_path)
    request_dir = tmp_path / ".automo/capabilities/requests"
    request_dir.mkdir(parents=True, exist_ok=True)
    (request_dir / "CAP-001.yaml").write_text(
        """id: CAP-001
experiment: EXP-001
capability:
  id: beta-calibrator
  kind: research-runtime
reason: missing capability
contract:
  inputs: [predictions]
  outputs: [calibrator]
requirements: [implement calibrator protocol]
acceptance: [tests pass]
scope:
  allowed_paths: [src, tests]
  forbidden_paths: [.automo]
""", encoding="utf-8"
    )
    result = RUNNER.invoke(app, ["capability", "handoff", "CAP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    handoff = tmp_path / ".automo/capabilities/handoffs/CAP-001-getdone.md"
    assert handoff.is_file()
    assert "GetDone" in handoff.read_text(encoding="utf-8")
    assert not (tmp_path / ".agent").exists()
