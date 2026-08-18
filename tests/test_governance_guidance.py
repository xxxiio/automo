from pathlib import Path

from typer.testing import CliRunner

from automo.cli import app
from automo.governance import (
    CandidateInput,
    EvaluationDepth,
    GovernanceError,
    HypothesisStatus,
    ModelRelationKind,
    ModelRole,
    ResearchGovernance,
)
from automo.guidance import select_guidance
from automo.ux import initialise_mr_project

RUNNER = CliRunner()


def test_governance_supports_model_graph_and_hypothesis_tree(tmp_path: Path) -> None:
    governance = ResearchGovernance(tmp_path)
    governance.initialise()
    governance.register_model("ranking", role=ModelRole.SUBMODEL)
    governance.register_model("ability", role=ModelRole.SUBMODEL)
    governance.register_model("meta", role=ModelRole.META)
    governance.add_model_relation("ranking", "meta", kind=ModelRelationKind.INPUT)
    governance.add_model_relation("ability", "meta", kind=ModelRelationKind.INPUT)
    governance.add_model_relation("ranking", "ability", kind=ModelRelationKind.CORRELATED)

    root = governance.create_hypothesis(
        "root",
        statement="The system has useful predictive value.",
        primary_model="meta",
        required_evaluation_depth=EvaluationDepth.SYSTEM,
    )
    child = governance.create_hypothesis(
        "ranking-info",
        parent_id=root.id,
        statement="Ranking contributes incremental predictive information.",
        primary_model="ranking",
        related_models=("meta",),
        required_evaluation_depth=EvaluationDepth.PARENT,
    )
    assert child.status == HypothesisStatus.PROPOSED
    governance.activate_hypothesis(child.id)
    assert governance.require_execution_ready().id == child.id
    assert governance.provenance("EXP-001").hypothesis_id == child.id
    done = governance.conclude_hypothesis(
        child.id,
        status=HypothesisStatus.SUPPORTED,
        conclusion="Parent-level evidence improved.",
    )
    assert done.status == HypothesisStatus.SUPPORTED
    assert governance.current_hypothesis() is None
    assert [item.id for _, item in governance.hypothesis_tree()] == ["root", "ranking-info"]


def test_no_active_hypothesis_blocks_research_execution(tmp_path: Path) -> None:
    governance = ResearchGovernance(tmp_path)
    governance.initialise()
    try:
        governance.require_execution_ready()
    except GovernanceError as exc:
        assert "no active research hypothesis" in str(exc)
    else:
        raise AssertionError("research execution must require an active hypothesis")


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


def test_hypothesis_cli_flow_and_model_relations(tmp_path: Path) -> None:
    initialise_mr_project(tmp_path)
    for model_id, role in (("ranking", "submodel"), ("meta", "meta")):
        result = RUNNER.invoke(
            app,
            [
                "research",
                "model-add",
                model_id,
                "--role",
                role,
                "--root",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
    result = RUNNER.invoke(
        app,
        [
            "research",
            "model-relation-add",
            "ranking",
            "meta",
            "--kind",
            "input",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    result = RUNNER.invoke(
        app,
        [
            "research",
            "hypothesis-create",
            "H-ROOT",
            "--statement",
            "System improves prediction.",
            "--primary-model",
            "meta",
            "--evaluation-depth",
            "system",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    result = RUNNER.invoke(
        app,
        [
            "research",
            "hypothesis-create",
            "H-RANK",
            "--statement",
            "Ranking adds information.",
            "--parent",
            "H-ROOT",
            "--primary-model",
            "ranking",
            "--related-model",
            "meta",
            "--objective",
            "ndcg:local:maximize",
            "--objective",
            "meta_log_loss:parent:minimize",
            "--evaluation-depth",
            "parent",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    result = RUNNER.invoke(
        app, ["research", "hypothesis-activate", "H-RANK", "--root", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    result = RUNNER.invoke(app, ["research", "hypothesis-tree", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "H-ROOT" in result.output and "H-RANK" in result.output
    result = RUNNER.invoke(
        app,
        [
            "research",
            "hypothesis-conclude",
            "H-RANK",
            "--status",
            "supported",
            "--conclusion",
            "Evidence supports incremental value.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output


def test_research_state_starts_at_schema_one_and_has_no_migration_command(tmp_path: Path) -> None:
    governance = ResearchGovernance(tmp_path)
    governance.initialise()
    project = (tmp_path / ".automo" / "project.yaml").read_text(encoding="utf-8")
    assert "schema_version: 1" in project
    result = RUNNER.invoke(app, ["migrate", "--root", str(tmp_path)])
    assert result.exit_code != 0


def test_initialise_rejects_incompatible_research_state_instead_of_migrating(
    tmp_path: Path,
) -> None:
    state = tmp_path / ".automo"
    state.mkdir()
    (state / "project.yaml").write_text(
        "artifact_type: automo.research_project\nschema_version: 99\n", encoding="utf-8"
    )
    try:
        ResearchGovernance(tmp_path).initialise()
    except GovernanceError as exc:
        assert "unsupported research-state schema_version" in str(exc)
    else:
        raise AssertionError("incompatible research state must be rejected")


def test_model_candidates_track_exact_composition_and_selection(tmp_path: Path) -> None:
    governance = ResearchGovernance(tmp_path)
    governance.initialise()
    governance.register_model("ranking", role=ModelRole.SUBMODEL)
    governance.register_model("market", role=ModelRole.SUBMODEL)
    governance.register_model("meta", role=ModelRole.META)
    governance.add_model_relation("ranking", "meta", kind=ModelRelationKind.INPUT)
    governance.add_model_relation("market", "meta", kind=ModelRelationKind.INPUT)

    governance.register_candidate(
        "RANK-v1", model_id="ranking", model_spec_id="rank-spec", artifact_id="registry/rank-v1"
    )
    governance.register_candidate(
        "MARKET-v1",
        model_id="market",
        model_spec_id="market-spec",
        artifact_id="registry/market-v1",
    )
    meta = governance.register_candidate(
        "META-v1",
        model_id="meta",
        model_spec_id="meta-linear",
        artifact_id="registry/meta-v1",
        inputs=(CandidateInput("ranking", "RANK-v1"), CandidateInput("market", "MARKET-v1")),
    )
    assert [item.candidate_id for item in meta.inputs] == ["RANK-v1", "MARKET-v1"]
    assert governance.select_candidate("META-v1").status.value == "selected"
    assert governance.selected_candidate("meta").id == "META-v1"


def test_composition_experiment_supports_ablation_and_meta_algorithm_comparison(
    tmp_path: Path,
) -> None:
    governance = ResearchGovernance(tmp_path)
    governance.initialise()
    governance.register_model("ranking", role=ModelRole.SUBMODEL)
    governance.register_model("market", role=ModelRole.SUBMODEL)
    governance.register_model("meta", role=ModelRole.META)
    governance.add_model_relation("ranking", "meta", kind=ModelRelationKind.INPUT)
    governance.add_model_relation("market", "meta", kind=ModelRelationKind.INPUT)
    governance.register_candidate(
        "RANK-v1", model_id="ranking", model_spec_id="rank-spec", artifact_id="rank"
    )
    governance.register_candidate(
        "MARKET-v1", model_id="market", model_spec_id="market-spec", artifact_id="market"
    )
    governance.register_candidate(
        "META-market",
        model_id="meta",
        model_spec_id="meta-linear",
        artifact_id="linear-market",
        inputs=(CandidateInput("market", "MARKET-v1"),),
    )
    governance.register_candidate(
        "META-market-rank",
        model_id="meta",
        model_spec_id="meta-linear",
        artifact_id="linear-market-rank",
        inputs=(CandidateInput("market", "MARKET-v1"), CandidateInput("ranking", "RANK-v1")),
    )
    governance.create_hypothesis(
        "H-COMP",
        statement="Ranking adds incremental information to meta.",
        primary_model="meta",
        related_models=("ranking",),
    )
    experiment = governance.create_composition_experiment(
        "EXP-COMP-1",
        hypothesis_id="H-COMP",
        target_model="meta",
        control_candidate_id="META-market",
        treatment_candidate_id="META-market-rank",
        metrics=("log_loss", "brier"),
        rationale="Isolate ranking incremental value.",
        expected_effect="Lower OOS log loss without calibration degradation.",
        falsification=("No committed metric improves.",),
    )
    assert experiment.control_candidate_id == "META-market"
    assert experiment.treatment_candidate_id == "META-market-rank"
    assert experiment.provenance.experiment_id == "EXP-COMP-1"
    assert experiment.kind.value == "input_ablation"


def test_candidate_cli_and_composition_cli(tmp_path: Path) -> None:
    initialise_mr_project(tmp_path)
    for model_id, role in (("ranking", "submodel"), ("market", "submodel"), ("meta", "meta")):
        result = RUNNER.invoke(
            app, ["research", "model-add", model_id, "--role", role, "--root", str(tmp_path)]
        )
        assert result.exit_code == 0, result.output
    for source in ("ranking", "market"):
        result = RUNNER.invoke(
            app,
            [
                "research",
                "model-relation-add",
                source,
                "meta",
                "--kind",
                "input",
                "--root",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
    for candidate, model in (("RANK-v1", "ranking"), ("MARKET-v1", "market")):
        result = RUNNER.invoke(
            app,
            [
                "research",
                "candidate-add",
                candidate,
                "--model",
                model,
                "--model-spec-id",
                f"{model}-spec",
                "--artifact-id",
                candidate.lower(),
                "--root",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
    for candidate, inputs in (
        ("META-market", ["market:MARKET-v1"]),
        ("META-market-rank", ["market:MARKET-v1", "ranking:RANK-v1"]),
    ):
        args = [
            "research",
            "candidate-add",
            candidate,
            "--model",
            "meta",
            "--model-spec-id",
            "meta-linear",
            "--artifact-id",
            candidate.lower(),
        ]
        for value in inputs:
            args += ["--input", value]
        args += ["--root", str(tmp_path)]
        result = RUNNER.invoke(app, args)
        assert result.exit_code == 0, result.output
    result = RUNNER.invoke(
        app,
        [
            "research",
            "hypothesis-create",
            "H-COMP",
            "--statement",
            "Ranking adds meta value.",
            "--primary-model",
            "meta",
            "--related-model",
            "ranking",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    result = RUNNER.invoke(
        app,
        [
            "research",
            "composition-create",
            "EXP-1",
            "--hypothesis",
            "H-COMP",
            "--target-model",
            "meta",
            "--control-candidate",
            "META-market",
            "--treatment-candidate",
            "META-market-rank",
            "--metric",
            "log_loss",
            "--rationale",
            "Ablate ranking.",
            "--expected-effect",
            "Improve log loss.",
            "--falsification",
            "No improvement.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output


def test_input_relations_are_acyclic_but_correlation_can_be_symmetric(tmp_path: Path) -> None:
    governance = ResearchGovernance(tmp_path)
    governance.initialise()
    governance.register_model("a", role=ModelRole.SUBMODEL)
    governance.register_model("b", role=ModelRole.META)
    governance.add_model_relation("a", "b", kind=ModelRelationKind.INPUT)
    try:
        governance.add_model_relation("b", "a", kind=ModelRelationKind.INPUT)
    except GovernanceError as exc:
        assert "model cycle" in str(exc)
    else:
        raise AssertionError("input dependency graph must remain acyclic")
    governance.add_model_relation("b", "a", kind=ModelRelationKind.CORRELATED)


def test_composition_experiment_rejects_confounded_spec_and_input_change(tmp_path: Path) -> None:
    governance = ResearchGovernance(tmp_path)
    governance.initialise()
    governance.register_model("input", role=ModelRole.SUBMODEL)
    governance.register_model("meta", role=ModelRole.META)
    governance.add_model_relation("input", "meta", kind=ModelRelationKind.INPUT)
    governance.register_candidate(
        "I1", model_id="input", model_spec_id="input-spec", artifact_id="i1"
    )
    governance.register_candidate("M1", model_id="meta", model_spec_id="linear", artifact_id="m1")
    governance.register_candidate(
        "M2",
        model_id="meta",
        model_spec_id="gbm",
        artifact_id="m2",
        inputs=(CandidateInput("input", "I1"),),
    )
    governance.create_hypothesis("H", statement="Composition helps.", primary_model="meta")
    try:
        governance.create_composition_experiment(
            "E",
            hypothesis_id="H",
            target_model="meta",
            control_candidate_id="M1",
            treatment_candidate_id="M2",
            metrics=("loss",),
            rationale="compare",
            expected_effect="improve",
            falsification=("no improvement",),
        )
    except GovernanceError as exc:
        assert "confounded" in str(exc)
    else:
        raise AssertionError("mixed composition and target-model changes must be rejected")
