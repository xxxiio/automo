from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from automo.research import InterventionKind, ResearchIntervention, apply_graph_intervention
from automo.runtime import (
    CrossFitSpec,
    DataInput,
    DataSnapshot,
    EvaluationContext,
    EvaluationSpec,
    GraphRuntime,
    MetricDirection,
    MetricScope,
    MetricSpec,
    ModelGraphSpec,
    ModelNodeSpec,
    ModelOutputBatch,
    ModelOutputInput,
    ModelSpec,
    ObjectiveSpec,
    PredictionRequest,
    ResearchPlugin,
    ResearchRuntime,
    TrainingRequest,
    TrainingResult,
)


@dataclass(frozen=True)
class MemorySource:
    id: str
    rows: tuple[Mapping[str, Any], ...]

    def snapshot(self) -> DataSnapshot:
        return DataSnapshot(self.id, self.rows, content_hash="fixture")


class ExternalFitService:
    def __init__(self) -> None:
        self.fit_partitions: list[str] = []
        self.evaluation_calls = 0

    def fit_action_policy(self, rows):
        self.fit_partitions.append("external")
        mean = sum(float(r["signal"]) for r in rows) / len(rows)
        return mean

    def score_actions(self, rows, actions):
        self.evaluation_calls += 1
        return sum(
            1.0
            for row, action in zip(rows, actions, strict=True)
            if action["take"] == (float(row["signal"]) >= 0.5)
        ) / len(rows)


class ActionPredictor:
    def __init__(self, threshold: float):
        self.threshold = threshold

    def predict(self, request: PredictionRequest) -> ModelOutputBatch:
        return ModelOutputBatch(
            tuple({"take": float(row["signal"]) >= self.threshold} for row in request.rows),
            output_name="action",
        )


class ExternalActionTrainer:
    implementation = "external.action"

    def fit(self, request: TrainingRequest) -> TrainingResult:
        service = request.services["external_fit"]
        threshold = service.fit_action_policy(request.rows)
        return TrainingResult(ActionPredictor(threshold), metadata={"source": "external-service"})


class ActionAccuracyEvaluator:
    id = "action_accuracy"

    def evaluate(self, context: EvaluationContext) -> float:
        return float(
            context.services["external_fit"].score_actions(context.rows, context.outputs.values)
        )


def test_custom_trainer_and_structured_evaluator_use_external_service() -> None:
    service = ExternalFitService()
    objective = ObjectiveSpec("action", target=None, implementation="structured")
    metric = MetricSpec("action_accuracy", MetricDirection.MAXIMIZE, MetricScope.DOWNSTREAM)
    spec = ModelSpec(
        "action-model",
        "external.action",
        None,
        objective,
        EvaluationSpec(metric),
        inputs=(DataInput(),),
    )
    source = MemorySource(
        "train", ({"signal": 0.1}, {"signal": 0.9}, {"signal": 0.8}, {"signal": 0.2})
    )
    plugin = ResearchPlugin(
        id="external-example",
        data_sources=(source,),
        feature_computers=(),
        feature_sets=(),
        objectives=(objective,),
        metrics=(),
        model_specs=(spec,),
        model_runners=(),
        model_trainers=(ExternalActionTrainer(),),
        evaluators=(ActionAccuracyEvaluator(),),
        services={"external_fit": service},
    )
    runtime = ResearchRuntime(plugin)
    model = runtime.fit("action-model", data_source_id="train")
    scores = runtime.evaluate("action-model", model, data_source_id="train")
    assert scores["action_accuracy"] == 1.0
    assert service.fit_partitions == ["external"]
    assert service.evaluation_calls == 1


class MemorizingPredictor:
    def __init__(self, memory):
        self.memory = dict(memory)

    def predict(self, request: PredictionRequest) -> ModelOutputBatch:
        return ModelOutputBatch(tuple(self.memory.get(row["id"], -999.0) for row in request.rows))


class MemorizingTrainer:
    implementation = "memorize"

    def fit(self, request: TrainingRequest) -> TrainingResult:
        return TrainingResult(
            MemorizingPredictor((row["id"], float(row["y"])) for row in request.rows)
        )


class MetaPredictor:
    def __init__(self, offset: float):
        self.offset = offset

    def predict(self, request: PredictionRequest) -> ModelOutputBatch:
        upstream = request.inputs["base"].values
        return ModelOutputBatch(tuple(float(value) + self.offset for value in upstream))


class LeakageCheckingMetaTrainer:
    implementation = "meta.check"

    def __init__(self) -> None:
        self.seen_upstream: tuple[float, ...] | None = None

    def fit(self, request: TrainingRequest) -> TrainingResult:
        upstream = tuple(float(v) for v in request.inputs["base"].values)
        self.seen_upstream = upstream
        # A memorizing upstream model would return true y in sample. OOF rows must instead be unseen.
        assert set(upstream) == {-999.0}
        return TrainingResult(MetaPredictor(1000.0))


class NumericEvaluator:
    id = "mse2"

    def evaluate(self, context: EvaluationContext) -> float:
        return sum(
            (float(row["y"]) - float(pred)) ** 2
            for row, pred in zip(context.rows, context.outputs.values, strict=True)
        ) / len(context.rows)


def test_meta_model_training_uses_cross_fitted_upstream_outputs() -> None:
    rows = tuple({"id": idx, "y": float(idx % 3)} for idx in range(12))
    source = MemorySource("fit", rows)
    base_obj = ObjectiveSpec("base-obj", target="y")
    meta_obj = ObjectiveSpec("meta-obj", target="y")
    metric = MetricSpec("mse2", MetricDirection.MINIMIZE)
    base = ModelSpec(
        "base", "memorize", None, base_obj, EvaluationSpec(metric), inputs=(DataInput(),)
    )
    meta = ModelSpec(
        "meta",
        "meta.check",
        None,
        meta_obj,
        EvaluationSpec(metric),
        inputs=(ModelOutputInput("base", alias="base"),),
    )
    meta_trainer = LeakageCheckingMetaTrainer()
    graph = ModelGraphSpec(
        "stack",
        (ModelNodeSpec("base", "base"), ModelNodeSpec("meta", "meta")),
        "meta",
        CrossFitSpec(folds=3, key="id", seed=11),
    )
    plugin = ResearchPlugin(
        id="stacking-example",
        data_sources=(source,),
        feature_computers=(),
        feature_sets=(),
        objectives=(base_obj, meta_obj),
        metrics=(),
        model_specs=(base, meta),
        model_runners=(),
        model_trainers=(MemorizingTrainer(), meta_trainer),
        evaluators=(NumericEvaluator(),),
        model_graphs=(graph,),
    )
    runtime = ResearchRuntime(plugin)
    graph_runtime = GraphRuntime(runtime)
    fitted = graph_runtime.fit("stack", rows=rows)
    assert fitted.cross_fit_metadata["leakage_safe_model_outputs"] == ("base",)
    assert meta_trainer.seen_upstream is not None
    # On held-out evaluation rows the full-fit base is unseen and returns -999; meta turns that into 1.
    heldout = tuple({"id": 100 + idx, "y": 1.0} for idx in range(4))
    scores = graph_runtime.evaluate("stack", fitted, rows=heldout, partition_id="oos")
    assert scores["mse2"] == 0.0


def test_graph_interventions_can_change_node_model_and_upstream_inputs() -> None:
    graph = ModelGraphSpec(
        "g",
        (
            ModelNodeSpec("base", "base-a"),
            ModelNodeSpec("meta", "meta", inputs=(ModelOutputInput("base", alias="base"),)),
        ),
        "meta",
    )
    changed = apply_graph_intervention(
        graph,
        ResearchIntervention(
            InterventionKind.NODE_MODEL, {"node_id": "base", "model_spec_id": "base-b"}
        ),
    )
    assert changed.nodes[0].model_spec_id == "base-b"
    removed = apply_graph_intervention(
        graph,
        ResearchIntervention(
            InterventionKind.MODEL_INPUT_REMOVAL, {"node_id": "meta", "upstream_node_id": "base"}
        ),
    )
    assert removed.nodes[1].inputs == ()


class DummyCodec:
    id = "dummy"

    def save(self, model, path):
        pass

    def load(self, path):
        raise NotImplementedError


def test_graph_registration_records_upstream_model_identity_and_cross_fit() -> None:
    rows = tuple({"id": idx, "y": float(idx % 2)} for idx in range(8))
    source = MemorySource("fit", rows)

    class RegisterableBase(MemorizingTrainer):
        artifact_codec = DummyCodec()

    class RegisterableMeta(LeakageCheckingMetaTrainer):
        artifact_codec = DummyCodec()

    obj = ObjectiveSpec("o", target="y")
    metric = MetricSpec("mse2", MetricDirection.MINIMIZE)
    base = ModelSpec("base", "memorize", None, obj, EvaluationSpec(metric), inputs=(DataInput(),))
    meta = ModelSpec(
        "meta",
        "meta.check",
        None,
        obj,
        EvaluationSpec(metric),
        inputs=(ModelOutputInput("base", alias="base"),),
    )
    graph = ModelGraphSpec(
        "stack",
        (ModelNodeSpec("base", "base"), ModelNodeSpec("meta", "meta")),
        "meta",
        CrossFitSpec(folds=2, key="id", seed=2),
    )
    plugin = ResearchPlugin(
        id="p",
        data_sources=(source,),
        feature_computers=(),
        feature_sets=(),
        objectives=(obj,),
        metrics=(),
        model_specs=(base, meta),
        model_runners=(),
        model_trainers=(RegisterableBase(), RegisterableMeta()),
        evaluators=(NumericEvaluator(),),
        model_graphs=(graph,),
    )
    runtime = ResearchRuntime(plugin)
    gr = GraphRuntime(runtime)
    fitted = gr.fit("stack", rows=rows)

    class FakeRegistry:
        def __init__(self):
            self.calls = []

        def register_model(self, model, **kwargs):
            self.calls.append(kwargs)
            return type("Manifest", (), {"id": f"MODEL-{len(self.calls)}"})()

    registry = FakeRegistry()
    ids = gr.register_graph(
        "stack",
        fitted,
        registry=registry,
        data_source_id="fit",
        data_snapshot_id="snap",
        data_snapshot_hash="hash",
    )
    assert ids == {"base": "MODEL-1", "meta": "MODEL-2"}
    meta_provenance = registry.calls[1]["provenance"]
    assert meta_provenance.model_graph_id == "stack"
    assert meta_provenance.upstream_model_ids == {"base": "MODEL-1"}
    assert meta_provenance.cross_fit_protocol["folds"] == 2
