from pathlib import Path

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


def _plugin(path: Path) -> ResearchPlugin:
    mse = MeanSquaredError()
    return ResearchPlugin(
        id="demo",
        data_sources=(CsvDataSource("train", path),),
        feature_computers=(
            LambdaFeature(FeatureSpec("x2", dependencies=("x",)), lambda row, r: float(r["x"]) * 2),
        ),
        feature_sets=(FeatureSetSpec("features", ("x2",)),),
        objectives=(ObjectiveSpec("regression", target="y"),),
        metrics=(mse,),
        model_specs=(
            ModelSpec(
                id="linear",
                implementation="linear.single_feature",
                feature_set="features",
                objective=ObjectiveSpec("regression", target="y"),
                evaluation=EvaluationSpec(
                    MetricSpec("mse", MetricDirection.MINIMIZE, MetricScope.LOCAL)
                ),
            ),
        ),
        model_runners=(SingleFeatureLinearRunner(),),
    )


def test_thin_plugin_uses_default_runtime(tmp_path: Path) -> None:
    data = tmp_path / "data.csv"
    data.write_text("x,y\n1,2\n2,4\n3,6\n", encoding="utf-8")
    runtime = ResearchRuntime(_plugin(data))
    model = runtime.fit("linear", data_source_id="train")
    result = runtime.evaluate("linear", model, data_source_id="train")
    assert result["mse"] < 1e-12


def test_metric_contract_has_direction_and_scope() -> None:
    metric = MetricSpec("roi", MetricDirection.MAXIMIZE, MetricScope.DOWNSTREAM)
    assert metric.direction.value == "maximize"
    assert metric.scope.value == "downstream"
