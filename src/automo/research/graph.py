from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from automo.runtime import GraphRuntime, ModelGraphSpec, ModelOutputInput
from automo.runtime.contracts import MetricDirection

from .contracts import InterventionKind, ResearchIntervention


class GraphResearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class GraphCandidateEvaluation:
    intervention: ResearchIntervention
    validation_metric: float
    oos_metric: float | None
    accepted: bool
    graph: ModelGraphSpec


def apply_graph_intervention(
    graph: ModelGraphSpec, intervention: ResearchIntervention
) -> ModelGraphSpec:
    values = intervention.values
    if intervention.kind == InterventionKind.NODE_MODEL:
        node_id = str(values["node_id"])
        model_spec_id = str(values["model_spec_id"])
        nodes = tuple(
            replace(node, model_spec_id=model_spec_id) if node.id == node_id else node
            for node in graph.nodes
        )
        if nodes == graph.nodes:
            raise GraphResearchError(f"unknown graph node: {node_id}")
        return replace(graph, id=f"{graph.id}__node-model", nodes=nodes)
    if intervention.kind in {
        InterventionKind.MODEL_INPUT_ADDITION,
        InterventionKind.MODEL_INPUT_REMOVAL,
    }:
        node_id = str(values["node_id"])
        upstream = str(values["upstream_node_id"])
        alias = str(values.get("alias", upstream))
        changed = False
        nodes = []
        for node in graph.nodes:
            if node.id != node_id:
                nodes.append(node)
                continue
            inputs = list(node.inputs)
            if intervention.kind == InterventionKind.MODEL_INPUT_ADDITION:
                if not any(
                    isinstance(item, ModelOutputInput) and item.node_id == upstream
                    for item in inputs
                ):
                    inputs.append(ModelOutputInput(upstream, alias=alias))
                    changed = True
            else:
                before = len(inputs)
                inputs = [
                    item
                    for item in inputs
                    if not (isinstance(item, ModelOutputInput) and item.node_id == upstream)
                ]
                changed = changed or len(inputs) != before
            nodes.append(replace(node, inputs=tuple(inputs)))
        if not changed:
            raise GraphResearchError("graph intervention made no change")
        return replace(graph, id=f"{graph.id}__input-change", nodes=tuple(nodes))
    raise GraphResearchError(f"unsupported graph intervention: {intervention.kind.value}")


def evaluate_graph_candidate(
    runtime: Any,
    *,
    baseline_graph_id: str,
    intervention: ResearchIntervention,
    fit_rows: Sequence[Mapping[str, Any]],
    validation_rows: Sequence[Mapping[str, Any]],
    oos_rows: Sequence[Mapping[str, Any]],
    minimum_improvement: float = 0.0,
) -> GraphCandidateEvaluation:
    graph_runtime = GraphRuntime(runtime)
    baseline = runtime.model_graphs[baseline_graph_id]
    candidate = apply_graph_intervention(baseline, intervention)
    runtime.model_graphs[candidate.id] = candidate
    baseline_fit = graph_runtime.fit(baseline.id, rows=fit_rows)
    candidate_fit = graph_runtime.fit(candidate.id, rows=fit_rows)
    baseline_val = next(
        iter(
            graph_runtime.evaluate(
                baseline.id, baseline_fit, rows=validation_rows, partition_id="validation"
            ).values()
        )
    )
    candidate_val = next(
        iter(
            graph_runtime.evaluate(
                candidate.id, candidate_fit, rows=validation_rows, partition_id="validation"
            ).values()
        )
    )
    output_node = next(node for node in candidate.nodes if node.id == candidate.output_node_id)
    spec = runtime.model_specs[output_node.model_spec_id]
    direction = spec.evaluation.primary.direction
    validation_improvement = (
        candidate_val - baseline_val
        if direction == MetricDirection.MAXIMIZE
        else baseline_val - candidate_val
    )
    if validation_improvement + 1e-15 < minimum_improvement:
        return GraphCandidateEvaluation(intervention, candidate_val, None, False, candidate)
    baseline_oos = next(
        iter(
            graph_runtime.evaluate(
                baseline.id, baseline_fit, rows=oos_rows, partition_id="research_oos"
            ).values()
        )
    )
    candidate_oos = next(
        iter(
            graph_runtime.evaluate(
                candidate.id, candidate_fit, rows=oos_rows, partition_id="research_oos"
            ).values()
        )
    )
    oos_improvement = (
        candidate_oos - baseline_oos
        if direction == MetricDirection.MAXIMIZE
        else baseline_oos - candidate_oos
    )
    return GraphCandidateEvaluation(
        intervention,
        candidate_val,
        candidate_oos,
        oos_improvement + 1e-15 >= minimum_improvement,
        candidate,
    )
