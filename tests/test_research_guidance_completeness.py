from __future__ import annotations

import re
from pathlib import Path

import yaml
from typer.testing import CliRunner

from automo.cli import app
from automo.guidance import select_guidance, task_classes, validate_guidance_pack

ROOT = Path(__file__).parents[1]
RUNNER = CliRunner()


def test_every_task_class_has_valid_bounded_guidance() -> None:
    assert validate_guidance_pack() == ()
    for task_class in task_classes():
        docs = select_guidance(task_class)
        assert 1 <= len(docs) <= 11
        assert len({doc.path for doc in docs}) == len(docs)
        assert all(doc.content.strip() for doc in docs)


def test_high_risk_tasks_load_required_safety_guidance() -> None:
    experiment = {doc.path for doc in select_guidance("experiment-design")}
    assert "policies/multiple-testing.md" in experiment
    assert "policies/early-stopping.md" in experiment
    assert "policies/sealed-oos.md" in experiment
    assert "acceptance/agent-adherence.md" in experiment

    meta = {doc.path for doc in select_guidance("meta-model-research")}
    assert "standards/leakage.md" in meta
    assert "references/meta-model-patterns.md" in meta
    assert "policies/multiple-testing.md" in meta

    diagnosis = {doc.path for doc in select_guidance("model-diagnosis")}
    assert "standards/diagnosis.md" in diagnosis
    assert "references/intervention-decision-table.md" in diagnosis


def test_guidance_documents_cover_pre_alpha_research_failure_modes() -> None:
    selected = {doc.path: doc.content for task in task_classes() for doc in select_guidance(task)}
    text = "\n".join(selected.values()).lower()
    for phrase in (
        "multiple-testing",
        "sealed oos",
        "early-stopping",
        "out-of-fold",
        "ablation",
        "inconclusive",
        "diminishing",
        "failed candidates",
        "capability request",
    ):
        assert phrase in text


def test_documented_automo_commands_exist() -> None:
    workflow_path = ROOT / "src/automo/skill/workflows/research-iteration.md"
    workflow = workflow_path.read_text(encoding="utf-8")
    commands = re.findall(r"`(automo [^`]+)`", workflow)
    assert commands
    for command in commands:
        parts = command.split()
        if "<task-class>" in parts:
            parts[parts.index("<task-class>")] = "experiment-design"
        args = parts[1:]
        # Documentation options are ignored; command path existence is checked via help.
        path = []
        for token in args:
            if token.startswith("-"):
                break
            path.append(token)
        result = RUNNER.invoke(app, [*path, "--help"])
        assert result.exit_code == 0, f"stale documented command {command}: {result.output}"


def test_multi_iteration_guidance_walkthrough_is_bounded_and_complete() -> None:
    path = ROOT / "examples/research-guidance/walkthrough.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    milestones = data["milestones"]
    assert len(milestones) >= 3
    assert {item["conclusion"] for item in milestones} >= {"accepted", "rejected"}
    for item in milestones:
        plan = item["plan"]
        assert plan["maximum_candidates"] >= len(item["experiments"])
        assert plan["maximum_oos_candidates"] >= 0
        assert plan["materiality_threshold"] > 0
        assert item["next_step"]
    forbidden = "\n".join(data["forbidden_actions"]).lower()
    assert "sealed oos" in forbidden
    assert "failed candidates" in forbidden
    assert "widen" in forbidden


def test_research_guidance_example_runs() -> None:
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    source_path = str(ROOT / "src")
    env["PYTHONPATH"] = source_path if not existing else f"{source_path}{os.pathsep}{existing}"
    completed = subprocess.run(
        [sys.executable, "examples/research-guidance/example.py"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "R001: rejected" in completed.stdout
    assert "R002: accepted" in completed.stdout
