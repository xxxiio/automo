from __future__ import annotations

from dataclasses import dataclass
import platform
import subprocess
from typing import Any

from .contracts import (
    EvaluationContext, ModelOutputBatch, PredictionRequest, ResearchPlugin, TrainingRequest,
)
from automo.registry import ModelRegistry, TrainingProvenance
from .features import FeatureEngine
from .graph import LegacyTrainerAdapter


class RuntimeContractError(RuntimeError):
    pass


@dataclass
class ResearchRuntime:
    plugin: ResearchPlugin

    def __post_init__(self) -> None:
        self.data_sources = self._unique(self.plugin.data_sources, "data source")
        self.feature_sets = self._unique(self.plugin.feature_sets, "feature set")
        self.objectives = self._unique(self.plugin.objectives, "objective")
        self.model_specs = self._unique(self.plugin.model_specs, "model spec")
        self.metrics = self._unique(self.plugin.metrics, "metric")
        self.model_runners = {item.implementation: item for item in self.plugin.model_runners}
        self.model_trainers = {item.implementation: item for item in self.plugin.model_trainers}
        self.evaluators = {item.id: item for item in self.plugin.evaluators}
        self.model_graphs = self._unique(self.plugin.model_graphs, "model graph")
        self.features = FeatureEngine(self.plugin.feature_computers)


    def trainer_for(self, implementation: str):
        if implementation in self.model_trainers:
            return self.model_trainers[implementation]
        if implementation in self.model_runners:
            return LegacyTrainerAdapter(self.model_runners[implementation], implementation)
        raise RuntimeContractError(f"no trainer or runner registered for {implementation}")

    def prepare_inputs(self, spec, rows):
        resolved = {}
        for inp in spec.resolved_inputs():
            from .contracts import FeatureSetInput, DataInput, ModelOutputInput
            if isinstance(inp, FeatureSetInput):
                resolved[inp.alias] = self.features.materialize(rows, self.feature_sets[inp.feature_set_id])
            elif isinstance(inp, DataInput):
                resolved[inp.alias] = tuple(rows)
            elif isinstance(inp, ModelOutputInput):
                raise RuntimeContractError("ModelOutputInput must be resolved by GraphRuntime")
        return resolved

    def evaluate_context(self, spec, context: EvaluationContext) -> dict[str, float]:
        contracts = (spec.evaluation.primary, *spec.evaluation.secondary)
        result = {}
        for metric in contracts:
            if metric.id in self.evaluators:
                result[metric.id] = float(self.evaluators[metric.id].evaluate(context))
                continue
            legacy = self.metrics.get(metric.id)
            if legacy is None:
                raise RuntimeContractError(f"no evaluator registered for metric {metric.id}")
            target_name = spec.objective.target
            if not target_name:
                raise RuntimeContractError(
                    f"legacy metric {metric.id} requires objective.target; register an Evaluator instead"
                )
            truth = tuple(float(row[target_name]) for row in context.rows)
            prediction = tuple(float(value) for value in context.outputs.values)
            result[metric.id] = float(legacy.evaluate(truth, prediction))
        return result

    @staticmethod
    def _unique(items: tuple[Any, ...], label: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for item in items:
            key = item.id
            if key in result:
                raise RuntimeContractError(f"duplicate {label}: {key}")
            result[key] = item
        return result

    def fit(self, model_id: str, *, data_source_id: str) -> Any:
        spec = self.model_specs[model_id]
        snapshot = self.data_sources[data_source_id].snapshot()
        trainer = self.trainer_for(spec.implementation)
        result = trainer.fit(
            TrainingRequest(
                model_spec=spec,
                rows=snapshot.rows,
                inputs=self.prepare_inputs(spec, snapshot.rows),
                objective=spec.objective,
                services=self.plugin.services,
                partition_id="fit",
            )
        )
        return result.predictor


    def fit_and_register(
        self,
        model_id: str,
        *,
        data_source_id: str,
        registry: ModelRegistry,
        registered_model_id: str | None = None,
        seed: int | None = None,
    ):
        spec = self.model_specs[model_id]
        snapshot = self.data_sources[data_source_id].snapshot()
        trainer = self.trainer_for(spec.implementation)
        codec = getattr(trainer, "artifact_codec", None)
        if codec is None and spec.implementation in self.model_runners:
            codec = getattr(self.model_runners[spec.implementation], "artifact_codec", None)
        if codec is None:
            raise RuntimeContractError(
                f"trainer {spec.implementation} does not expose an artifact_codec required for registration"
            )
        result = trainer.fit(
            TrainingRequest(
                model_spec=spec, rows=snapshot.rows,
                inputs=self.prepare_inputs(spec, snapshot.rows), objective=spec.objective,
                services=self.plugin.services, seed=seed, partition_id="fit",
            )
        )
        feature_set_id = spec.feature_set or "<custom-inputs>"
        provenance = TrainingProvenance(
            data_source_id=data_source_id, data_snapshot_id=snapshot.id,
            data_snapshot_hash=snapshot.content_hash, feature_set_id=feature_set_id,
            model_spec_id=spec.id, objective_id=spec.objective.id,
            runner_implementation=spec.implementation, python_version=platform.python_version(),
            seed=seed, code_revision=self._git_revision(),
        )
        registry_model = result.artifacts.get("registry_model", result.predictor)
        return registry.register_model(
            registry_model, implementation=spec.implementation, model_spec_id=spec.id,
            objective_id=spec.objective.id, feature_set_id=feature_set_id, provenance=provenance,
            codec=codec, model_id=registered_model_id,
        )

    def evaluate_and_record(
        self,
        model_id: str,
        model: Any,
        *,
        data_source_id: str,
        registry: Any,
        registered_model_id: str,
        split: str = "evaluation",
    ) -> dict[str, float]:
        spec = self.model_specs[model_id]
        snapshot = self.data_sources[data_source_id].snapshot()
        metrics = self.evaluate(model_id, model, data_source_id=data_source_id)
        metric_specs = {item.id: item for item in (spec.evaluation.primary, *spec.evaluation.secondary)}
        for metric_id, value in metrics.items():
            contract = metric_specs[metric_id]
            registry.append_benchmark(
                registered_model_id,
                metric_id=metric_id,
                direction=contract.direction,
                scope=contract.scope,
                value=value,
                sample_count=len(snapshot.rows),
                split=split,
            )
        return metrics

    @staticmethod
    def _git_revision() -> str | None:
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    def evaluate(self, model_id: str, model: Any, *, data_source_id: str) -> dict[str, float]:
        spec = self.model_specs[model_id]
        snapshot = self.data_sources[data_source_id].snapshot()
        inputs = self.prepare_inputs(spec, snapshot.rows)
        request = PredictionRequest(
            model_spec=spec, rows=snapshot.rows, inputs=inputs,
            services=self.plugin.services, partition_id="evaluation",
        )
        if hasattr(model, "predict"):
            try:
                output = model.predict(request)
            except (TypeError, AttributeError):
                values = model.predict(inputs.get("features", snapshot.rows))
                output = ModelOutputBatch(tuple(values))
        else:
            raise RuntimeContractError("fitted predictor does not implement predict")
        if not isinstance(output, ModelOutputBatch):
            output = ModelOutputBatch(tuple(output))
        context = EvaluationContext(
            model_spec=spec, rows=snapshot.rows, outputs=output, objective=spec.objective,
            inputs=inputs, services=self.plugin.services, partition_id="evaluation",
        )
        return self.evaluate_context(spec, context)

