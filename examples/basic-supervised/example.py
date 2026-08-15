from pathlib import Path
from tempfile import TemporaryDirectory

from automo.runtime import (
    CsvDataSource,
    EvaluationSpec,
    FeatureSetSpec,
    FeatureSpec,
    LambdaFeature,
    MeanSquaredError,
    MetricDirection,
    MetricSpec,
    ModelSpec,
    ObjectiveSpec,
    ResearchPlugin,
    ResearchRuntime,
    SingleFeatureLinearRunner,
)

with TemporaryDirectory() as tmp:
    path = Path(tmp) / "data.csv"
    path.write_text("x,y\n1,2\n2,4\n3,6\n", encoding="utf-8")
    objective = ObjectiveSpec("regression", target="y")
    evaluation = EvaluationSpec(MetricSpec("mse", MetricDirection.MINIMIZE))
    plugin = ResearchPlugin(
        id="basic",
        data_sources=(CsvDataSource("data", path),),
        feature_computers=(LambdaFeature(FeatureSpec("x"), lambda row, _: float(row["x"])),),
        feature_sets=(FeatureSetSpec("features", ("x",)),),
        objectives=(objective,),
        metrics=(MeanSquaredError(),),
        model_specs=(
            ModelSpec(
                "linear",
                "linear.single_feature",
                "features",
                objective,
                evaluation,
            ),
        ),
        model_runners=(SingleFeatureLinearRunner(),),
    )
    runtime = ResearchRuntime(plugin)
    model = runtime.fit("linear", data_source_id="data")
    print(runtime.evaluate("linear", model, data_source_id="data"))
