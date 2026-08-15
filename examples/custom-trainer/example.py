from automo.runtime import (
    DataInput,
    DataSnapshot,
    EvaluationContext,
    EvaluationSpec,
    MetricDirection,
    MetricSpec,
    ModelOutputBatch,
    ModelSpec,
    ObjectiveSpec,
    PredictionRequest,
    ResearchPlugin,
    ResearchRuntime,
    TrainingRequest,
    TrainingResult,
)


class Source:
    id = "demo"

    def snapshot(self):
        return DataSnapshot("demo", ({"x": 0.1}, {"x": 0.9}, {"x": 0.8}, {"x": 0.2}))


class ExternalService:
    def fit(self, rows):
        return sum(float(row["x"]) for row in rows) / len(rows)


class Predictor:
    def __init__(self, threshold):
        self.threshold = threshold

    def predict(self, request: PredictionRequest):
        values = tuple(float(row["x"]) >= self.threshold for row in request.rows)
        return ModelOutputBatch(values, "decision")


class Trainer:
    implementation = "example.external"

    def fit(self, request: TrainingRequest):
        return TrainingResult(Predictor(request.services["external"].fit(request.rows)))


class Evaluator:
    id = "agreement"

    def evaluate(self, context: EvaluationContext):
        expected = tuple(float(row["x"]) >= 0.5 for row in context.rows)
        matches = zip(expected, context.outputs.values, strict=True)
        return sum(a == b for a, b in matches) / len(expected)


objective = ObjectiveSpec("decision", target=None, implementation="structured")
metric = MetricSpec("agreement", MetricDirection.MAXIMIZE)
spec = ModelSpec(
    "model",
    "example.external",
    None,
    objective,
    EvaluationSpec(metric),
    inputs=(DataInput(),),
)
plugin = ResearchPlugin(
    id="custom-trainer",
    data_sources=(Source(),),
    feature_computers=(),
    feature_sets=(),
    objectives=(objective,),
    metrics=(),
    model_specs=(spec,),
    model_runners=(),
    model_trainers=(Trainer(),),
    evaluators=(Evaluator(),),
    services={"external": ExternalService()},
)
runtime = ResearchRuntime(plugin)
model = runtime.fit("model", data_source_id="demo")
print(runtime.evaluate("model", model, data_source_id="demo"))
