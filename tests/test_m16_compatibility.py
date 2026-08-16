from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from automo.cli import app
from automo.guidance import guidance_lock, select_guidance, validate_project_agent
from automo.refresh import (
    CalibrationPolicy,
    ModelPoolSpec,
    RetentionPolicy,
    SelectionPolicy,
    TrainingPolicy,
)
from automo.registry import ModelManifest, TrainingProvenance
from automo.runtime import MetricDirection

RUNNER = CliRunner()


def test_data_only_model_provenance_can_omit_feature_set() -> None:
    provenance = TrainingProvenance(
        data_source_id="data",
        data_snapshot_id="snap",
        data_snapshot_hash=None,
        feature_set_id=None,
        model_spec_id="raw",
        objective_id="obj",
        runner_implementation="custom",
        python_version="3.13",
    )
    manifest = ModelManifest(
        id="MODEL-1",
        implementation="custom",
        model_spec_id="raw",
        objective_id="obj",
        feature_set_id=None,
        artifact_codec="codec",
        artifact_path="x",
        artifact_hash="h",
        provenance_path="p",
    )
    assert provenance.feature_set_id is None
    assert manifest.feature_set_id is None


def test_pool_can_describe_heterogeneous_comparable_specs() -> None:
    pool = ModelPoolSpec(
        id="pool",
        objective_id="obj",
        model_spec_id=None,
        model_spec_ids=("a", "b"),
        primary_metric_id="m",
        primary_metric_direction=MetricDirection.MAXIMIZE,
        training_policy=TrainingPolicy("train"),
        calibration_policy=CalibrationPolicy("cal"),
        retention_policy=RetentionPolicy("keep"),
        selection_policy=SelectionPolicy("select"),
    )
    assert pool.resolved_model_spec_ids == ("a", "b")


def _project_agent(root: Path) -> None:
    base = root / ".project-agent" / "automo"
    (base / "research").mkdir(parents=True)
    (base / "AGENTS.md").write_text("# Project research rules\n", encoding="utf-8")
    (base / "research/ranking.md").write_text(
        "# Ranking research\nUse point-in-time evidence.\n", encoding="utf-8"
    )
    (base / "index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "infer": [],
                "rules": [
                    {
                        "id": "ranking",
                        "concerns": ["model-research", "experiment-design"],
                        "load": ["research/ranking.md"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_project_agent_guidance_is_additive_and_disableable(tmp_path: Path) -> None:
    _project_agent(tmp_path)
    docs = select_guidance("experiment-design", project_root=tmp_path)
    paths = {d.path for d in docs}
    assert "policies/sealed-oos.md" in paths
    assert ".project-agent/automo/AGENTS.md" in paths
    assert ".project-agent/automo/research/ranking.md" in paths
    builtin = select_guidance("experiment-design", project_root=tmp_path, use_project_agent=False)
    assert all(d.source == "builtin" for d in builtin)


def test_project_agent_uses_explicit_concerns(tmp_path: Path) -> None:
    _project_agent(tmp_path)
    docs = select_guidance("model-diagnosis", project_root=tmp_path, concerns=("model-research",))
    assert any(d.path.endswith("research/ranking.md") for d in docs)


def test_guidance_lock_detects_project_agent_drift(tmp_path: Path) -> None:
    (tmp_path / ".automo").mkdir()
    _project_agent(tmp_path)
    assert guidance_lock(tmp_path)[0] == "missing"
    assert guidance_lock(tmp_path, write=True)[0] == "written"
    assert guidance_lock(tmp_path)[0] == "current"
    (tmp_path / ".project-agent/automo/research/ranking.md").write_text(
        "# Ranking research\nChanged.\n", encoding="utf-8"
    )
    assert guidance_lock(tmp_path)[0] == "drift"


def test_project_agent_rejects_path_escape(tmp_path: Path) -> None:
    base = tmp_path / ".project-agent" / "automo"
    base.mkdir(parents=True)
    (base / "index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "rules": [
                    {"id": "bad", "concerns": ["experiment-design"], "load": ["../secret.md"]}
                ],
            }
        ),
        encoding="utf-8",
    )
    assert validate_project_agent(tmp_path)


def test_guidance_cli_matches_getdone_style_project_agent_switch(tmp_path: Path) -> None:
    _project_agent(tmp_path)
    result = RUNNER.invoke(
        app,
        ["guidance", "--task-class", "experiment-design", "--root", str(tmp_path), "--paths-only"],
    )
    assert result.exit_code == 0
    assert ".project-agent/automo/research/ranking.md" in result.stdout
    result = RUNNER.invoke(
        app,
        [
            "guidance",
            "--task-class",
            "experiment-design",
            "--root",
            str(tmp_path),
            "--no-project-agent",
            "--paths-only",
        ],
    )
    assert result.exit_code == 0
    assert ".project-agent" not in result.stdout


def test_project_agent_infers_concerns_from_changed_paths(tmp_path: Path) -> None:
    base = tmp_path / ".project-agent" / "automo"
    (base / "data").mkdir(parents=True)
    (base / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
    (base / "data/pit.md").write_text("# Point in time\n", encoding="utf-8")
    (base / "index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "infer": [{"paths": ["src/data/**"], "concerns": ["point-in-time"]}],
                "rules": [{"id": "pit", "concerns": ["point-in-time"], "load": ["data/pit.md"]}],
            }
        ),
        encoding="utf-8",
    )
    docs = select_guidance(
        "experiment-design", project_root=tmp_path, changed_paths=("src/data/feed.py",)
    )
    assert any(doc.path.endswith("data/pit.md") for doc in docs)


def test_research_plan_conformance_rejects_confounded_or_duplicate_work() -> None:
    from automo.research import (
        CandidateProposal,
        InterventionKind,
        ResearchBudget,
        ResearchIntervention,
        ResearchPlan,
        ResearchSafeguards,
        ResearchSearchSpace,
        validate_research_plan,
    )

    intervention = ResearchIntervention(InterventionKind.PARAMETERS, {"depth": 3})
    candidate = CandidateProposal(
        "c1", "base", intervention, ("diagnosis",), "improve metric", ("no lift",), 1
    )
    plan = ResearchPlan(
        "p",
        "base",
        "data",
        "split",
        "diagnosis",
        (),
        ResearchSearchSpace("space", maximum_compound_interventions=2),
        ResearchBudget(maximum_candidates=2, maximum_model_fits=2, maximum_oos_candidates=1),
        ResearchSafeguards(minimum_improvement=-0.1),
        (
            candidate,
            CandidateProposal("c2", "base", intervention, ("same",), "same", ("no lift",), 2),
        ),
    )
    errors = validate_research_plan(plan)
    assert any("compound" in error for error in errors)
    assert any("duplicate" in error for error in errors)
    assert any("degradation" in error for error in errors)


def test_automo_ignores_root_project_agent_owned_by_getdone(tmp_path: Path) -> None:
    root_agent = tmp_path / ".project-agent"
    root_agent.mkdir()
    (root_agent / "AGENTS.md").write_text("# GetDone project agent\n", encoding="utf-8")
    (root_agent / "getdone-only.md").write_text("# Development only\n", encoding="utf-8")
    (root_agent / "index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "rules": [
                    {"id": "dev", "concerns": ["experiment-design"], "load": ["getdone-only.md"]}
                ],
            }
        ),
        encoding="utf-8",
    )
    docs = select_guidance("experiment-design", project_root=tmp_path)
    assert all(not doc.path.startswith(".project-agent/") for doc in docs)
    assert validate_project_agent(tmp_path) == ()
    assert guidance_lock(tmp_path)[1]["project_agent_digest"] is None


def test_automo_init_namespaces_project_agent_without_touching_getdone_root(tmp_path: Path) -> None:
    root_agent = tmp_path / ".project-agent"
    root_agent.mkdir()
    getdone_index = root_agent / "index.json"
    getdone_index.write_text('{"schema_version": 1, "rules": []}\n', encoding="utf-8")
    from automo.ux import initialise_mr_project

    initialise_mr_project(tmp_path)
    assert getdone_index.read_text(encoding="utf-8") == '{"schema_version": 1, "rules": []}\n'
    assert (tmp_path / ".project-agent/automo/index.json").is_file()
    assert (tmp_path / ".project-agent/automo/AGENTS.md").is_file()
