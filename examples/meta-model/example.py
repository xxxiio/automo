from automo.runtime import (
    CrossFitSpec, DataInput, EvaluationContext, EvaluationSpec, GraphRuntime, MetricDirection,
    MetricSpec, ModelGraphSpec, ModelNodeSpec, ModelOutputBatch, ModelOutputInput, ModelSpec,
    ObjectiveSpec, PredictionRequest, ResearchPlugin, ResearchRuntime, TrainingRequest, TrainingResult,
)
from automo.runtime.contracts import DataSnapshot

class Source:
    id = "fit"
    def snapshot(self):
        return DataSnapshot("fit", tuple({"id": i, "y": float(i % 3)} for i in range(12)))

class BasePredictor:
    def __init__(self, seen): self.seen = dict(seen)
    def predict(self, request: PredictionRequest):
        return ModelOutputBatch(tuple(self.seen.get(row["id"], -1.0) for row in request.rows))

class BaseTrainer:
    implementation = "demo.base"
    def fit(self, request: TrainingRequest):
        return TrainingResult(BasePredictor((row["id"], float(row["y"])) for row in request.rows))

class MetaPredictor:
    def predict(self, request: PredictionRequest):
        return ModelOutputBatch(tuple(float(v) + 2.0 for v in request.inputs["base"].values))

class MetaTrainer:
    implementation = "demo.meta"
    def fit(self, request: TrainingRequest):
        # Upstream fit inputs are out-of-fold predictions, so memorized training values never appear.
        assert set(request.inputs["base"].values) == {-1.0}
        return TrainingResult(MetaPredictor())

class MSE:
    id = "mse"
    def evaluate(self, context: EvaluationContext):
        return sum((float(row["y"]) - float(pred)) ** 2 for row, pred in zip(context.rows, context.outputs.values, strict=True)) / len(context.rows)

objective = ObjectiveSpec("regression", target="y")
metric = MetricSpec("mse", MetricDirection.MINIMIZE)
base = ModelSpec("base", "demo.base", None, objective, EvaluationSpec(metric), inputs=(DataInput(),))
meta = ModelSpec("meta", "demo.meta", None, objective, EvaluationSpec(metric), inputs=(ModelOutputInput("base", alias="base"),))
graph = ModelGraphSpec("stack", (ModelNodeSpec("base", "base"), ModelNodeSpec("meta", "meta")), "meta", CrossFitSpec(folds=3, key="id"))
plugin = ResearchPlugin(
    id="meta-example", data_sources=(Source(),), feature_computers=(), feature_sets=(), objectives=(objective,), metrics=(),
    model_specs=(base, meta), model_runners=(), model_trainers=(BaseTrainer(), MetaTrainer()), evaluators=(MSE(),), model_graphs=(graph,),
)
runtime = ResearchRuntime(plugin)
rows = plugin.data_sources[0].snapshot().rows
fitted = GraphRuntime(runtime).fit("stack", rows=rows)
print(fitted.cross_fit_metadata)
