from pathlib import Path
from tempfile import TemporaryDirectory

from automo.registry import FilesystemModelRegistry
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
from automo.runtime.builtins import LinearModelJsonCodec


with TemporaryDirectory() as tmp:
    root = Path(tmp)
    data_path = root / "data.csv"
    data_path.write_text("id,x,y\n1,1,2\n2,2,4\n3,3,6\n4,4,8\n", encoding="utf-8")

    objective = ObjectiveSpec("regression", target="y")
    evaluation = EvaluationSpec(MetricSpec("mse", MetricDirection.MINIMIZE))
    spec = ModelSpec("linear", "linear.single_feature", "features", objective, evaluation)
    plugin = ResearchPlugin(
        id="end-to-end",
        data_sources=(CsvDataSource("training", data_path),),
        feature_computers=(LambdaFeature(FeatureSpec("x"), lambda row, _: float(row["x"])),),
        feature_sets=(FeatureSetSpec("features", ("x",)),),
        objectives=(objective,),
        metrics=(MeanSquaredError(),),
        model_specs=(spec,),
        model_runners=(SingleFeatureLinearRunner(),),
    )

    runtime = ResearchRuntime(plugin)
    registry = FilesystemModelRegistry(root / ".automo" / "registry", codecs=(LinearModelJsonCodec(),))
    manifest = runtime.fit_and_register("linear", data_source_id="training", registry=registry, seed=42)
    model = registry.load_model(manifest.id)
    metrics = runtime.evaluate_and_record(
        "linear",
        model,
        data_source_id="training",
        registry=registry,
        registered_model_id=manifest.id,
        split="example",
    )

    print(f"registered={manifest.id}")
    print(f"status={registry.status(manifest.id).value}")
    print(f"mse={metrics['mse']:.6f}")
