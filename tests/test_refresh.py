from __future__ import annotations

from pathlib import Path

import pytest

from automo.refresh import (
    AffineCalibrator,
    CalibrationPolicy,
    DataIteration,
    FilesystemPoolStore,
    HashSplit,
    ModelPoolSpec,
    OrderedSplit,
    PredefinedSplit,
    RefreshService,
    RetentionPolicy,
    SelectionPolicy,
    TrainingPolicy,
)
from automo.registry import FilesystemModelRegistry, ModelStatus
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


def _runtime(tmp_path: Path, rows: str) -> tuple[ResearchRuntime, Path]:
    data = tmp_path / "data.csv"
    data.write_text(rows, encoding="utf-8")
    objective = ObjectiveSpec("regression", target="y")
    plugin = ResearchPlugin(
        id="refresh-demo",
        data_sources=(CsvDataSource("all", data),),
        feature_computers=(LambdaFeature(FeatureSpec("x"), lambda row, _: float(row["x"])),),
        feature_sets=(FeatureSetSpec("features", ("x",)),),
        objectives=(objective,),
        metrics=(MeanSquaredError(),),
        model_specs=(
            ModelSpec(
                id="linear",
                implementation="linear.single_feature",
                feature_set="features",
                objective=objective,
                evaluation=EvaluationSpec(
                    MetricSpec("mse", MetricDirection.MINIMIZE, MetricScope.LOCAL)
                ),
            ),
        ),
        model_runners=(SingleFeatureLinearRunner(),),
    )
    return ResearchRuntime(plugin), data


def _pool(*, recalibrate: bool = False, retrain: bool = False, top_k: int = 2) -> ModelPoolSpec:
    return ModelPoolSpec(
        id="pool-regression",
        objective_id="regression",
        model_spec_id="linear",
        primary_metric_id="mse",
        primary_metric_direction=MetricDirection.MINIMIZE,
        training_policy=TrainingPolicy("train", each_iteration=retrain, min_new_observations=2),
        calibration_policy=CalibrationPolicy(
            "cal",
            each_iteration=recalibrate,
            min_fit_observations=2,
            calibrator="affine" if recalibrate else None,
        ),
        retention_policy=RetentionPolicy("retain", top_k=top_k, minimum_test_observations=1),
        selection_policy=SelectionPolicy("select"),
    )


def _active_model(runtime: ResearchRuntime, registry: FilesystemModelRegistry) -> str:
    manifest = runtime.fit_and_register("linear", data_source_id="all", registry=registry)
    registry.transition(manifest.id, ModelStatus.VALIDATED, reason="validated")
    registry.transition(manifest.id, ModelStatus.ACTIVE, reason="active")
    return manifest.id


def test_ordered_split_supports_plain_integer_id_without_datetime(tmp_path: Path) -> None:
    runtime, _ = _runtime(tmp_path, "id,x,y\n30,3,6\n10,1,2\n20,2,4\n40,4,8\n50,5,10\n")
    snapshot = runtime.data_sources["all"].snapshot()
    parts = OrderedSplit("id", fit_fraction=0.4, validation_fraction=0.2, test_fraction=0.4).split(
        snapshot
    )
    assert parts.fit.row_indices == (1, 2)
    assert parts.validation.row_indices == (0,)
    assert parts.test.row_indices == (3, 4)


def test_hash_split_is_deterministic_for_unordered_ids(tmp_path: Path) -> None:
    runtime, _ = _runtime(
        tmp_path,
        "id,x,y\na,1,2\nb,2,4\nc,3,6\nd,4,8\ne,5,10\nf,6,12\ng,7,14\nh,8,16\ni,9,18\nj,10,20\n",
    )
    snapshot = runtime.data_sources["all"].snapshot()
    split = HashSplit("id", seed=7, fit_fraction=0.5, validation_fraction=0.2, test_fraction=0.3)
    assert split.split(snapshot) == split.split(snapshot)


def test_refresh_recalibration_uses_fit_then_validation_then_test(tmp_path: Path) -> None:
    # Base model is trained on first linear regime, then refresh data has shifted scale.
    runtime, data = _runtime(
        tmp_path,
        "id,x,y\n1,1,2\n2,2,4\n3,3,6\n4,4,8\n5,5,10\n6,6,12\n7,7,14\n8,8,16\n9,9,18\n10,10,20\n",
    )
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    model_id = _active_model(runtime, registry)
    data.write_text(
        "id,x,y\n1,1,4\n2,2,8\n3,3,12\n4,4,16\n5,5,20\n6,6,24\n7,7,28\n8,8,32\n9,9,36\n10,10,40\n",
        encoding="utf-8",
    )
    snapshot = runtime.data_sources["all"].snapshot()
    iteration = DataIteration("ITER-1", snapshot.id, snapshot.content_hash)
    service = RefreshService(
        runtime,
        registry,
        FilesystemPoolStore(tmp_path / ".automo/pools"),
        calibrators=(AffineCalibrator(),),
    )
    report = service.run(
        _pool(recalibrate=True),
        iteration,
        PredefinedSplit((0, 1, 2, 3), (4, 5, 6), (7, 8, 9)),
        data_source_id="all",
    )
    card = report["scorecards"][0]
    assert card["model_id"] == model_id
    assert card["calibration_id"] is not None
    assert card["validation_count"] == 3 and card["test_count"] == 3
    assert report["refresh_oos_used_only_after_variant_freeze"] is True
    assert registry.calibrations(model_id)


def test_refresh_retraining_creates_new_model_identity_and_ranks_on_test(tmp_path: Path) -> None:
    runtime, data = _runtime(tmp_path, "id,x,y\n1,1,2\n2,2,4\n3,3,6\n4,4,8\n5,5,10\n6,6,12\n")
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    original = _active_model(runtime, registry)
    data.write_text(
        "id,x,y\n1,1,3\n2,2,6\n3,3,9\n4,4,12\n5,5,15\n6,6,18\n7,7,21\n8,8,24\n9,9,27\n",
        encoding="utf-8",
    )
    snapshot = runtime.data_sources["all"].snapshot()
    service = RefreshService(runtime, registry, FilesystemPoolStore(tmp_path / ".automo/pools"))
    report = service.run(
        _pool(retrain=True),
        DataIteration("ITER-2", snapshot.id, snapshot.content_hash),
        PredefinedSplit((0, 1, 2), (3, 4, 5), (6, 7, 8)),
        data_source_id="all",
    )
    retrained = [x for x in report["scorecards"] if x["source"] == "retrained"]
    assert retrained and retrained[0]["model_id"] != original
    assert registry.get_manifest(original).id == original
    assert report["retained_model_ids"][0] == retrained[0]["model_id"]


def test_refresh_dry_run_does_not_create_refresh_artifacts(tmp_path: Path) -> None:
    runtime, _ = _runtime(tmp_path, "id,x,y\n1,1,2\n2,2,4\n3,3,6\n4,4,8\n5,5,10\n")
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    _active_model(runtime, registry)
    snapshot = runtime.data_sources["all"].snapshot()
    root = tmp_path / ".automo"
    service = RefreshService(runtime, registry, FilesystemPoolStore(root / "pools"))
    plan = service.run(
        _pool(),
        DataIteration("ITER-3", snapshot.id, snapshot.content_hash),
        OrderedSplit("id", 0.4, 0.2, 0.4),
        data_source_id="all",
        dry_run=True,
    )
    assert plan["counts"] == {"fit": 2, "validation": 1, "test": 2}
    assert not (root / "refresh" / "ITER-3").exists()


def test_refresh_records_benchmarks_and_lifecycle_pool_state(tmp_path: Path) -> None:
    runtime, _ = _runtime(tmp_path, "id,x,y\n1,1,2\n2,2,4\n3,3,6\n4,4,8\n5,5,10\n6,6,12\n")
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    model_id = _active_model(runtime, registry)
    snapshot = runtime.data_sources["all"].snapshot()
    service = RefreshService(runtime, registry, FilesystemPoolStore(tmp_path / ".automo/pools"))
    service.run(
        _pool(top_k=1),
        DataIteration("ITER-4", snapshot.id, snapshot.content_hash),
        PredefinedSplit((0, 1), (2, 3), (4, 5)),
        data_source_id="all",
    )
    assert {b.split for b in registry.benchmarks(model_id)} >= {"refresh_validation", "refresh_oos"}
    pool_snapshot = FilesystemPoolStore(tmp_path / ".automo/pools").history("pool-regression")[-1]
    assert pool_snapshot.selected_model_ids == (model_id,)
    assert registry.status(model_id) is ModelStatus.ACTIVE


def test_retention_stability_gate_can_degrade_model(tmp_path: Path) -> None:
    runtime, data = _runtime(tmp_path, "id,x,y\n1,1,2\n2,2,4\n3,3,6\n4,4,8\n5,5,10\n6,6,12\n")
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    model_id = _active_model(runtime, registry)
    data.write_text("id,x,y\n1,1,2\n2,2,4\n3,3,6\n4,4,8\n5,5,100\n6,6,120\n", encoding="utf-8")
    snapshot = runtime.data_sources["all"].snapshot()
    pool = ModelPoolSpec(
        id="pool-regression",
        objective_id="regression",
        model_spec_id="linear",
        primary_metric_id="mse",
        primary_metric_direction=MetricDirection.MINIMIZE,
        training_policy=TrainingPolicy("train"),
        calibration_policy=CalibrationPolicy("cal"),
        retention_policy=RetentionPolicy(
            "retain", top_k=1, maximum_validation_test_degradation=1.0
        ),
        selection_policy=SelectionPolicy("select"),
    )
    RefreshService(runtime, registry, FilesystemPoolStore(tmp_path / ".automo/pools")).run(
        pool,
        DataIteration("ITER-5", snapshot.id, snapshot.content_hash),
        PredefinedSplit((0, 1), (2, 3), (4, 5)),
        data_source_id="all",
    )
    assert registry.status(model_id) is ModelStatus.DEGRADED
    assert (
        FilesystemPoolStore(tmp_path / ".automo/pools")
        .history("pool-regression")[-1]
        .active_model_ids
        == ()
    )


def test_refresh_and_pool_cli_work_with_id_only_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    from automo.cli import app

    data = tmp_path / "data.csv"
    data.write_text("id,x,y\n1,1,2\n2,2,4\n3,3,6\n4,4,8\n5,5,10\n6,6,12\n", encoding="utf-8")
    module = tmp_path / "demo_refresh_plugin.py"
    module.write_text(
        "from pathlib import Path\n"
        "from automo.runtime import *\n"
        "from automo.refresh import *\n"
        f"DATA = Path({str(data)!r})\n"
        "def create_plugin():\n"
        "    objective=ObjectiveSpec('regression', target='y')\n"
        "    pool=ModelPoolSpec('pool-regression','regression','linear','mse',MetricDirection.MINIMIZE,TrainingPolicy('train'),CalibrationPolicy('cal'),RetentionPolicy('retain',top_k=1),SelectionPolicy('select'))\n"
        "    return ResearchPlugin(id='demo',data_sources=(CsvDataSource('all',DATA),),feature_computers=(LambdaFeature(FeatureSpec('x'),lambda row,_: float(row['x'])),),feature_sets=(FeatureSetSpec('features',('x',)),),objectives=(objective,),metrics=(MeanSquaredError(),),model_specs=(ModelSpec('linear','linear.single_feature','features',objective,EvaluationSpec(MetricSpec('mse',MetricDirection.MINIMIZE,MetricScope.LOCAL))),),model_runners=(SingleFeatureLinearRunner(),),model_pools=(pool,),split_strategies=(OrderedSplit('id',.4,.2,.4),))\n",
        encoding="utf-8",
    )
    (tmp_path / "automo.toml").write_text(
        '[project]\nplugin = "demo_refresh_plugin:create_plugin"\n', encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    runtime = ResearchRuntime(__import__("demo_refresh_plugin").create_plugin())
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    model_id = _active_model(runtime, registry)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "refresh",
            "--pool",
            "pool-regression",
            "--data-source",
            "all",
            "--split",
            "ordered",
            "--iteration",
            "ITER-CLI",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    pool = runner.invoke(app, ["models", "pool", "pool-regression", "--root", str(tmp_path)])
    assert pool.exit_code == 0 and model_id in pool.stdout
    history = runner.invoke(app, ["refresh", "history", "--root", str(tmp_path)])
    assert history.exit_code == 0 and "ITER-CLI" in history.stdout
