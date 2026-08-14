from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping, Sequence

from .contracts import (
    DataInput,
    EvaluationContext,
    FeatureSetInput,
    GraphTrainingResult,
    ModelGraphSpec,
    ModelOutputBatch,
    ModelOutputInput,
    ModelSpec,
    PredictionRequest,
    TrainingRequest,
    TrainingResult,
)


class GraphContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class LegacyPredictorAdapter:
    model: Any

    def predict(self, request: PredictionRequest) -> ModelOutputBatch:
        values = self.model.predict(request.inputs.get("features", request.rows))
        return ModelOutputBatch(tuple(values))


@dataclass(frozen=True)
class LegacyTrainerAdapter:
    runner: Any
    implementation: str

    @property
    def artifact_codec(self):
        return getattr(self.runner, "artifact_codec", None)

    def fit(self, request: TrainingRequest) -> TrainingResult:
        target_name = request.objective.target
        if not target_name:
            raise GraphContractError(
                f"legacy runner {self.implementation} requires objective.target"
            )
        features = request.inputs.get("features")
        if features is None:
            raise GraphContractError("legacy runner requires a FeatureSetInput")
        target = tuple(float(row[target_name]) for row in request.rows)
        fitted = self.runner.fit(request.model_spec, features, target=target)
        return TrainingResult(predictor=LegacyPredictorAdapter(fitted), artifacts={"registry_model": fitted})


class GraphRuntime:
    """Leakage-safe model graph trainer/evaluator.

    Upstream outputs consumed by another node are cross-fitted on the fit partition.
    Final node predictors are subsequently trained using those OOF inputs. For validation
    or OOS evaluation, all upstream predictors are the frozen full-fit predictors.
    """

    def __init__(self, runtime: Any):
        self.runtime = runtime

    def fit(self, graph_id: str, *, rows: Sequence[Mapping[str, Any]], seed: int | None = None) -> GraphTrainingResult:
        graph = self.runtime.model_graphs[graph_id]
        ordered = self._topological_order(graph)
        results: dict[str, TrainingResult] = {}
        oof_cache: dict[str, ModelOutputBatch] = {}
        fold_assignments = self._fold_assignments(rows, graph.cross_fit.folds, graph.cross_fit.key, graph.cross_fit.seed)

        for node in ordered:
            spec = self.runtime.model_specs[node.model_spec_id]
            node_inputs = node.inputs or spec.resolved_inputs()
            resolved: dict[str, Any] = {}
            for inp in node_inputs:
                if isinstance(inp, FeatureSetInput):
                    feature_set = self.runtime.feature_sets[inp.feature_set_id]
                    resolved[inp.alias] = self.runtime.features.materialize(rows, feature_set)
                elif isinstance(inp, DataInput):
                    resolved[inp.alias] = tuple(rows)
                elif isinstance(inp, ModelOutputInput):
                    if inp.node_id not in results:
                        raise GraphContractError(f"upstream node {inp.node_id} is not available")
                    if inp.node_id not in oof_cache:
                        oof_cache[inp.node_id] = self._cross_fit_output(
                            graph,
                            upstream_node_id=inp.node_id,
                            rows=rows,
                            fold_assignments=fold_assignments,
                            seed=seed,
                        )
                    resolved[inp.resolved_alias] = oof_cache[inp.node_id]
                else:
                    raise GraphContractError(f"unsupported model input: {type(inp).__name__}")
            trainer = self.runtime.trainer_for(spec.implementation)
            results[node.id] = trainer.fit(
                TrainingRequest(
                    model_spec=spec,
                    rows=tuple(rows),
                    inputs=resolved,
                    objective=spec.objective,
                    services=self.runtime.plugin.services,
                    seed=seed,
                    partition_id="fit",
                )
            )

        return GraphTrainingResult(
            graph_id=graph.id,
            node_results=results,
            cross_fit_metadata={
                "folds": graph.cross_fit.folds,
                "key": graph.cross_fit.key,
                "seed": graph.cross_fit.seed,
                "leakage_safe_model_outputs": tuple(sorted(oof_cache)),
            },
        )

    def predict(
        self,
        graph_id: str,
        fitted: GraphTrainingResult,
        *,
        rows: Sequence[Mapping[str, Any]],
        partition_id: str = "evaluation",
    ) -> Mapping[str, ModelOutputBatch]:
        graph = self.runtime.model_graphs[graph_id]
        outputs: dict[str, ModelOutputBatch] = {}
        for node in self._topological_order(graph):
            spec = self.runtime.model_specs[node.model_spec_id]
            resolved = self._prediction_inputs(node.inputs or spec.resolved_inputs(), rows, outputs)
            predictor = fitted.node_results[node.id].predictor
            outputs[node.id] = predictor.predict(
                PredictionRequest(
                    model_spec=spec,
                    rows=tuple(rows),
                    inputs=resolved,
                    services=self.runtime.plugin.services,
                    partition_id=partition_id,
                )
            )
        return outputs

    def evaluate(
        self,
        graph_id: str,
        fitted: GraphTrainingResult,
        *,
        rows: Sequence[Mapping[str, Any]],
        partition_id: str = "evaluation",
    ) -> dict[str, float]:
        graph = self.runtime.model_graphs[graph_id]
        outputs = self.predict(graph_id, fitted, rows=rows, partition_id=partition_id)
        node = next(item for item in graph.nodes if item.id == graph.output_node_id)
        spec = self.runtime.model_specs[node.model_spec_id]
        resolved = self._prediction_inputs(node.inputs or spec.resolved_inputs(), rows, outputs, exclude=node.id)
        context = EvaluationContext(
            model_spec=spec,
            rows=tuple(rows),
            outputs=outputs[node.id],
            objective=spec.objective,
            inputs=resolved,
            services=self.runtime.plugin.services,
            partition_id=partition_id,
        )
        return self.runtime.evaluate_context(spec, context)

    def register_graph(
        self,
        graph_id: str,
        fitted: GraphTrainingResult,
        *,
        registry: Any,
        data_source_id: str,
        data_snapshot_id: str,
        data_snapshot_hash: str | None = None,
    ) -> Mapping[str, str]:
        from automo.registry import TrainingProvenance
        import platform

        graph = self.runtime.model_graphs[graph_id]
        registered: dict[str, str] = {}
        for node in self._topological_order(graph):
            spec = self.runtime.model_specs[node.model_spec_id]
            trainer = self.runtime.trainer_for(spec.implementation)
            codec = getattr(trainer, "artifact_codec", None)
            if codec is None:
                raise GraphContractError(f"trainer {spec.implementation} lacks artifact_codec required for graph registration")
            result = fitted.node_results[node.id]
            artifact = result.artifacts.get("registry_model", result.predictor)
            dependencies = {
                inp.node_id: registered[inp.node_id]
                for inp in (node.inputs or spec.resolved_inputs())
                if isinstance(inp, ModelOutputInput)
            }
            provenance = TrainingProvenance(
                data_source_id=data_source_id,
                data_snapshot_id=data_snapshot_id,
                data_snapshot_hash=data_snapshot_hash,
                feature_set_id=spec.feature_set or "<graph-inputs>",
                model_spec_id=spec.id,
                objective_id=spec.objective.id,
                runner_implementation=spec.implementation,
                python_version=platform.python_version(),
                code_revision=self.runtime._git_revision(),
                model_graph_id=graph.id,
                upstream_model_ids=dependencies,
                cross_fit_protocol=dict(fitted.cross_fit_metadata),
            )
            manifest = registry.register_model(
                artifact, implementation=spec.implementation, model_spec_id=spec.id,
                objective_id=spec.objective.id, feature_set_id=spec.feature_set or "<graph-inputs>",
                provenance=provenance, codec=codec,
            )
            registered[node.id] = manifest.id
        return registered

    def _cross_fit_output(
        self,
        graph: ModelGraphSpec,
        *,
        upstream_node_id: str,
        rows: Sequence[Mapping[str, Any]],
        fold_assignments: tuple[int, ...],
        seed: int | None,
    ) -> ModelOutputBatch:
        node = next(item for item in graph.nodes if item.id == upstream_node_id)
        spec = self.runtime.model_specs[node.model_spec_id]
        # Cross-fitting is intentionally limited to upstream nodes that do not themselves
        # depend on model outputs in this first public contract. Nested stacking can be
        # added without changing the public request/result contracts.
        if any(isinstance(inp, ModelOutputInput) for inp in (node.inputs or spec.resolved_inputs())):
            raise GraphContractError("nested model-output cross fitting is not yet supported")
        out: list[Any] = [None] * len(rows)
        for fold in range(graph.cross_fit.folds):
            train_rows = tuple(row for idx, row in enumerate(rows) if fold_assignments[idx] != fold)
            holdout_indices = tuple(idx for idx in range(len(rows)) if fold_assignments[idx] == fold)
            holdout_rows = tuple(rows[idx] for idx in holdout_indices)
            train_inputs = self._base_inputs(node.inputs or spec.resolved_inputs(), train_rows)
            trainer = self.runtime.trainer_for(spec.implementation)
            result = trainer.fit(
                TrainingRequest(
                    model_spec=spec,
                    rows=train_rows,
                    inputs=train_inputs,
                    objective=spec.objective,
                    services=self.runtime.plugin.services,
                    seed=seed,
                    partition_id=f"cross-fit-{fold}-train",
                )
            )
            holdout_inputs = self._base_inputs(node.inputs or spec.resolved_inputs(), holdout_rows)
            batch = result.predictor.predict(
                PredictionRequest(
                    model_spec=spec,
                    rows=holdout_rows,
                    inputs=holdout_inputs,
                    services=self.runtime.plugin.services,
                    partition_id=f"cross-fit-{fold}-holdout",
                )
            )
            for idx, value in zip(holdout_indices, batch.values, strict=True):
                out[idx] = value
        if any(value is None for value in out):
            raise GraphContractError("cross-fitting did not produce every upstream output")
        return ModelOutputBatch(tuple(out))

    def _base_inputs(self, inputs: Sequence[Any], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for inp in inputs:
            if isinstance(inp, FeatureSetInput):
                resolved[inp.alias] = self.runtime.features.materialize(rows, self.runtime.feature_sets[inp.feature_set_id])
            elif isinstance(inp, DataInput):
                resolved[inp.alias] = tuple(rows)
            elif isinstance(inp, ModelOutputInput):
                raise GraphContractError("model-output input requires graph resolution")
        return resolved

    def _prediction_inputs(
        self,
        inputs: Sequence[Any],
        rows: Sequence[Mapping[str, Any]],
        outputs: Mapping[str, ModelOutputBatch],
        *,
        exclude: str | None = None,
    ) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for inp in inputs:
            if isinstance(inp, FeatureSetInput):
                resolved[inp.alias] = self.runtime.features.materialize(rows, self.runtime.feature_sets[inp.feature_set_id])
            elif isinstance(inp, DataInput):
                resolved[inp.alias] = tuple(rows)
            elif isinstance(inp, ModelOutputInput):
                if inp.node_id == exclude:
                    continue
                resolved[inp.resolved_alias] = outputs[inp.node_id]
        return resolved

    @staticmethod
    def _fold_assignments(rows: Sequence[Mapping[str, Any]], folds: int, key: str | None, seed: int) -> tuple[int, ...]:
        values: list[int] = []
        for idx, row in enumerate(rows):
            token = row.get(key) if key else idx
            digest = hashlib.sha256(f"{seed}:{token}".encode()).digest()
            values.append(int.from_bytes(digest[:8], "big") % folds)
        if len(set(values)) < 2 and len(rows) >= 2:
            values = [idx % folds for idx in range(len(rows))]
        return tuple(values)

    def _topological_order(self, graph: ModelGraphSpec):
        nodes = {node.id: node for node in graph.nodes}
        deps = {
            node.id: {
                inp.node_id
                for inp in (node.inputs or self.runtime.model_specs[node.model_spec_id].resolved_inputs())
                if isinstance(inp, ModelOutputInput)
            }
            for node in graph.nodes
        }
        ordered = []
        ready = sorted(node_id for node_id, required in deps.items() if not required)
        while ready:
            node_id = ready.pop(0)
            ordered.append(nodes[node_id])
            for other in sorted(deps):
                if node_id in deps[other]:
                    deps[other].remove(node_id)
                    if not deps[other] and nodes[other] not in ordered and other not in ready:
                        ready.append(other); ready.sort()
        if len(ordered) != len(nodes):
            raise GraphContractError("model graph contains a cycle or missing dependency")
        return tuple(ordered)
