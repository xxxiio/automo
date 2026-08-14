from __future__ import annotations

from pathlib import Path

import pytest

from automo.refresh import AffineCalibrator, PredefinedSplit
from automo.registry import FilesystemModelRegistry
from automo.research import (
    FilesystemResearchStore,
    InterventionKind,
    ResearchBudget,
    ResearchError,
    ResearchSafeguards,
    ResearchSearchSpace,
    ResearchService,
)
from automo.runtime import (
    CsvDataSource,
    EvaluationSpec,
    FeatureSetSpec,
    FeatureSpec,
    LambdaFeature,
    MeanSquaredError,
    MetricDirection,
    MetricScope,
    MetricSpec,
    ModelSpec,
    ObjectiveSpec,
    ResearchPlugin,
    ResearchRuntime,
    SingleFeatureLinearRunner,
)


def _runtime(tmp_path: Path) -> ResearchRuntime:
    data = tmp_path / "data.csv"
    data.write_text(
        "id,x,x2,y\n"
        "1,1,1,2\n2,2,4,4\n3,3,9,6\n4,4,16,8\n5,5,25,10\n"
        "6,6,36,12\n7,7,49,14\n8,8,64,16\n9,9,81,18\n10,10,100,20\n",
        encoding="utf-8",
    )
    objective = ObjectiveSpec("regression", target="y")
    evaluation = EvaluationSpec(MetricSpec("mse", MetricDirection.MINIMIZE, MetricScope.LOCAL))
    plugin = ResearchPlugin(
        id="research-demo",
        data_sources=(CsvDataSource("all", data),),
        feature_computers=(
            LambdaFeature(FeatureSpec("x"), lambda row, _: float(row["x"])),
            LambdaFeature(FeatureSpec("x2"), lambda row, _: float(row["x2"])),
        ),
        feature_sets=(FeatureSetSpec("good", ("x",)), FeatureSetSpec("bad", ("x2",))),
        objectives=(objective,), metrics=(MeanSquaredError(),),
        model_specs=(
            ModelSpec("baseline", "linear.single_feature", "bad", objective, evaluation),
            ModelSpec("good-model", "linear.single_feature", "good", objective, evaluation),
        ),
        model_runners=(SingleFeatureLinearRunner(),),
        calibrators=(AffineCalibrator(),),
        split_strategies=(PredefinedSplit((0,1,2,3), (4,5,6), (7,8,9), id="predefined"),),
    )
    return ResearchRuntime(plugin)


def test_evidence_directed_plan_is_bounded_and_explicit(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    store = FilesystemResearchStore(tmp_path / ".automo/research")
    service = ResearchService(runtime, split_strategies=runtime.plugin.split_strategies, store=store)
    plan = service.plan(
        iteration_id="RESEARCH-0001", baseline_model_spec_id="baseline", data_source_id="all",
        split_strategy_id="predefined", diagnosis="underfitting", findings=("baseline misses linear signal",),
        search_space=ResearchSearchSpace("space", model_spec_ids=("baseline","good-model"), feature_set_ids=("good",), calibrator_ids=("affine",)),
        budget=ResearchBudget(maximum_candidates=2, maximum_model_fits=4, maximum_oos_candidates=1),
        safeguards=ResearchSafeguards(minimum_improvement=0.01),
    )
    assert len(plan.candidates) == 2
    assert all(c.intervention.kind in {InterventionKind.MODEL, InterventionKind.FEATURE_SET} for c in plan.candidates)
    assert all(c.falsification and c.fingerprint for c in plan.candidates)


def test_candidate_history_blocks_duplicate_research(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    store = FilesystemResearchStore(tmp_path / ".automo/research")
    service = ResearchService(runtime, split_strategies=runtime.plugin.split_strategies, store=store)
    kwargs = dict(
        baseline_model_spec_id="baseline", data_source_id="all", split_strategy_id="predefined",
        diagnosis="feature_gap", findings=("missing useful feature",),
        search_space=ResearchSearchSpace("space", feature_set_ids=("good",)),
        budget=ResearchBudget(maximum_candidates=1, maximum_model_fits=3, maximum_oos_candidates=1),
        safeguards=ResearchSafeguards(),
    )
    service.plan(iteration_id="RESEARCH-0001", **kwargs)
    with pytest.raises(ResearchError, match="no untested candidates"):
        service.plan(iteration_id="RESEARCH-0002", **kwargs)


def test_progressive_evaluation_caps_oos_and_registers_accepted_model(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    for runner in runtime.plugin.model_runners:
        registry.register_codec(runner.artifact_codec)
    store = FilesystemResearchStore(tmp_path / ".automo/research")
    service = ResearchService(runtime, split_strategies=runtime.plugin.split_strategies, store=store, registry=registry)
    plan = service.plan(
        iteration_id="RESEARCH-0003", baseline_model_spec_id="baseline", data_source_id="all",
        split_strategy_id="predefined", diagnosis="underfitting", findings=("baseline underfits",),
        search_space=ResearchSearchSpace("space", model_spec_ids=("good-model",), feature_set_ids=("good",)),
        budget=ResearchBudget(maximum_candidates=2, maximum_model_fits=4, maximum_oos_candidates=1),
        safeguards=ResearchSafeguards(minimum_improvement=0.01, minimum_validation_observations=2, minimum_oos_observations=2),
    )
    report = service.execute(plan)
    assert report.validation_trials == 2
    assert report.oos_trials == 1
    accepted = [r for r in report.results if r.stage.value == "accepted"]
    assert accepted and accepted[0].registered_model_id is not None
    assert len(registry.list_models()) == 1


def test_calibration_search_is_allowed_for_calibration_diagnosis(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    store = FilesystemResearchStore(tmp_path / ".automo/research")
    service = ResearchService(runtime, split_strategies=runtime.plugin.split_strategies, store=store)
    plan = service.plan(
        iteration_id="RESEARCH-0004", baseline_model_spec_id="good-model", data_source_id="all",
        split_strategy_id="predefined", diagnosis="poor_calibration", findings=("calibration drift",),
        search_space=ResearchSearchSpace("space", calibrator_ids=("affine",)),
        budget=ResearchBudget(maximum_candidates=1, maximum_model_fits=3, maximum_oos_candidates=1),
        safeguards=ResearchSafeguards(),
    )
    assert plan.candidates[0].intervention.kind is InterventionKind.CALIBRATION
    report = service.execute(plan)
    assert report.validation_trials == 1
    assert report.oos_trials <= 1


def test_research_cli_plan_run_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner
    from automo.cli import app

    data = tmp_path / "data.csv"
    data.write_text("id,x,x2,y\n1,1,1,2\n2,2,4,4\n3,3,9,6\n4,4,16,8\n5,5,25,10\n6,6,36,12\n7,7,49,14\n8,8,64,16\n9,9,81,18\n10,10,100,20\n", encoding="utf-8")
    module = tmp_path / "demo_research_plugin.py"
    module.write_text(
        "from pathlib import Path\n"
        "from automo.runtime import *\n"
        "from automo.refresh import *\n"
        "from automo.research import ResearchSearchSpace\n"
        f"DATA=Path({str(data)!r})\n"
        "def create_plugin():\n"
        " o=ObjectiveSpec('regression',target='y'); e=EvaluationSpec(MetricSpec('mse',MetricDirection.MINIMIZE,MetricScope.LOCAL))\n"
        " return ResearchPlugin(id='demo',data_sources=(CsvDataSource('all',DATA),),feature_computers=(LambdaFeature(FeatureSpec('x'),lambda r,_:float(r['x'])),LambdaFeature(FeatureSpec('x2'),lambda r,_:float(r['x2']))),feature_sets=(FeatureSetSpec('good',('x',)),FeatureSetSpec('bad',('x2',))),objectives=(o,),metrics=(MeanSquaredError(),),model_specs=(ModelSpec('baseline','linear.single_feature','bad',o,e),ModelSpec('good-model','linear.single_feature','good',o,e)),model_runners=(SingleFeatureLinearRunner(),),split_strategies=(PredefinedSplit((0,1,2,3),(4,5,6),(7,8,9),id='predefined'),),research_spaces=(ResearchSearchSpace('default',model_spec_ids=('good-model',),feature_set_ids=('good',)),))\n",
        encoding="utf-8",
    )
    (tmp_path / "automo.toml").write_text('[project]\nplugin = "demo_research_plugin:create_plugin"\n', encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    runner = CliRunner()
    planned = runner.invoke(app, ["research", "plan", "R-CLI", "--baseline", "baseline", "--data-source", "all", "--split", "predefined", "--space", "default", "--diagnosis", "underfitting", "--maximum-oos-candidates", "1", "--root", str(tmp_path)])
    assert planned.exit_code == 0, planned.output
    executed = runner.invoke(app, ["research", "run", "R-CLI", "--space", "default", "--root", str(tmp_path)])
    assert executed.exit_code == 0, executed.output
    history = runner.invoke(app, ["research", "history", "--root", str(tmp_path)])
    assert history.exit_code == 0 and "R-CLI" in history.output
    candidates = runner.invoke(app, ["research", "candidates", "R-CLI", "--root", str(tmp_path)])
    assert candidates.exit_code == 0 and "CANDIDATE" in candidates.output


def test_parameter_intervention_executes_within_budget(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    store = FilesystemResearchStore(tmp_path / ".automo/research")
    service = ResearchService(runtime, split_strategies=runtime.plugin.split_strategies, store=store)
    plan = service.plan(
        iteration_id="RESEARCH-0005", baseline_model_spec_id="baseline", data_source_id="all",
        split_strategy_id="predefined", diagnosis="overfitting", findings=("regularize candidate",),
        search_space=ResearchSearchSpace("space", parameter_choices={"regularization": (1.0,)}),
        budget=ResearchBudget(maximum_candidates=1, maximum_model_fits=2, maximum_oos_candidates=1),
        safeguards=ResearchSafeguards(),
    )
    assert plan.candidates[0].intervention.kind is InterventionKind.PARAMETERS
    report = service.execute(plan)
    assert report.validation_trials == 1


def test_missing_candidate_capability_persists_bounded_request(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    # Add a candidate spec whose implementation has no registered runner.
    bad = ModelSpec(
        "missing-runner", "not.installed", "good", runtime.objectives["regression"],
        runtime.model_specs["baseline"].evaluation,
    )
    runtime.model_specs[bad.id] = bad
    store = FilesystemResearchStore(tmp_path / ".automo/research")
    service = ResearchService(runtime, split_strategies=runtime.plugin.split_strategies, store=store)
    plan = service.plan(
        iteration_id="RESEARCH-0006", baseline_model_spec_id="baseline", data_source_id="all",
        split_strategy_id="predefined", diagnosis="underfitting", findings=("try new family",),
        search_space=ResearchSearchSpace("space", model_spec_ids=("missing-runner",)),
        budget=ResearchBudget(maximum_candidates=1, maximum_model_fits=2, maximum_oos_candidates=1),
        safeguards=ResearchSafeguards(),
    )
    report = service.execute(plan)
    assert report.results[0].stage.value == "blocked"
    requests = list((tmp_path / "research/capabilities/requests").glob("CAPABILITY-*.yaml"))
    assert len(requests) == 1
