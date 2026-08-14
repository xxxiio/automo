from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Protocol, Sequence


class MetricDirection(StrEnum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class MetricScope(StrEnum):
    LOCAL = "local"
    DOWNSTREAM = "downstream"
    RISK = "risk"
    OPERATIONAL = "operational"


@dataclass(frozen=True)
class DataSnapshot:
    id: str
    rows: tuple[Mapping[str, Any], ...]
    as_of_field: str | None = None
    content_hash: str | None = None


class DataSource(Protocol):
    id: str
    def snapshot(self) -> DataSnapshot: ...


@dataclass(frozen=True)
class FeatureSpec:
    id: str
    dependencies: tuple[str, ...] = ()
    version: str = "1"
    point_in_time_safe: bool = True


@dataclass(frozen=True)
class FeatureSetSpec:
    id: str
    features: tuple[str, ...]
    description: str | None = None

    def __post_init__(self) -> None:
        if len(set(self.features)) != len(self.features):
            raise ValueError("feature set contains duplicate feature ids")


class FeatureComputer(Protocol):
    spec: FeatureSpec
    def compute(self, row: Mapping[str, Any], resolved: Mapping[str, Any]) -> Any: ...


@dataclass(frozen=True)
class ObjectiveSpec:
    id: str
    target: str | None = None
    implementation: str = "supervised"
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MetricSpec:
    id: str
    direction: MetricDirection
    scope: MetricScope = MetricScope.LOCAL
    implementation: str = "builtin"
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationSpec:
    primary: MetricSpec
    secondary: tuple[MetricSpec, ...] = ()


@dataclass(frozen=True)
class FeatureSetInput:
    feature_set_id: str
    alias: str = "features"


@dataclass(frozen=True)
class DataInput:
    alias: str = "data"


@dataclass(frozen=True)
class ModelOutputInput:
    node_id: str
    output: str = "prediction"
    alias: str | None = None

    @property
    def resolved_alias(self) -> str:
        return self.alias or self.node_id


ModelInput = FeatureSetInput | DataInput | ModelOutputInput


@dataclass(frozen=True)
class ModelSpec:
    id: str
    implementation: str
    feature_set: str | None
    objective: ObjectiveSpec
    evaluation: EvaluationSpec
    params: Mapping[str, Any] = field(default_factory=dict)
    inputs: tuple[ModelInput, ...] = ()

    def resolved_inputs(self) -> tuple[ModelInput, ...]:
        if self.inputs:
            return self.inputs
        if self.feature_set is None:
            return (DataInput(),)
        return (FeatureSetInput(self.feature_set),)


@dataclass(frozen=True)
class ModelOutputBatch:
    values: tuple[Any, ...]
    output_name: str = "prediction"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.values)


class FittedModel(Protocol):
    def predict(self, rows: Sequence[Mapping[str, Any]]) -> Sequence[Any]: ...


class ModelRunner(Protocol):
    """Legacy supervised runner contract kept for compatibility."""
    implementation: str
    def fit(
        self,
        spec: ModelSpec,
        rows: Sequence[Mapping[str, Any]],
        *,
        target: Sequence[float],
    ) -> FittedModel: ...


@dataclass(frozen=True)
class TrainingRequest:
    model_spec: ModelSpec
    rows: tuple[Mapping[str, Any], ...]
    inputs: Mapping[str, Any]
    objective: ObjectiveSpec
    services: Mapping[str, Any] = field(default_factory=dict)
    seed: int | None = None
    partition_id: str = "fit"


@dataclass(frozen=True)
class TrainingResult:
    predictor: Any
    artifacts: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ModelTrainer(Protocol):
    implementation: str
    def fit(self, request: TrainingRequest) -> TrainingResult: ...


@dataclass(frozen=True)
class PredictionRequest:
    model_spec: ModelSpec
    rows: tuple[Mapping[str, Any], ...]
    inputs: Mapping[str, Any]
    services: Mapping[str, Any] = field(default_factory=dict)
    partition_id: str = "evaluation"


class Predictor(Protocol):
    def predict(self, request: PredictionRequest) -> ModelOutputBatch: ...


@dataclass(frozen=True)
class EvaluationContext:
    model_spec: ModelSpec
    rows: tuple[Mapping[str, Any], ...]
    outputs: ModelOutputBatch
    objective: ObjectiveSpec
    inputs: Mapping[str, Any] = field(default_factory=dict)
    services: Mapping[str, Any] = field(default_factory=dict)
    partition_id: str = "evaluation"


class Evaluator(Protocol):
    id: str
    def evaluate(self, context: EvaluationContext) -> float: ...


class Metric(Protocol):
    """Legacy numeric metric contract kept for compatibility."""
    id: str
    def evaluate(self, truth: Sequence[float], prediction: Sequence[float]) -> float: ...


@dataclass(frozen=True)
class CrossFitSpec:
    folds: int = 5
    key: str | None = None
    seed: int = 0

    def __post_init__(self) -> None:
        if self.folds < 2:
            raise ValueError("cross fitting requires at least two folds")


@dataclass(frozen=True)
class ModelNodeSpec:
    id: str
    model_spec_id: str
    inputs: tuple[ModelInput, ...] = ()
    output_name: str = "prediction"


@dataclass(frozen=True)
class ModelGraphSpec:
    id: str
    nodes: tuple[ModelNodeSpec, ...]
    output_node_id: str
    cross_fit: CrossFitSpec = field(default_factory=CrossFitSpec)

    def __post_init__(self) -> None:
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("model graph contains duplicate node ids")
        if self.output_node_id not in set(ids):
            raise ValueError("model graph output node is not registered")


@dataclass(frozen=True)
class GraphTrainingResult:
    graph_id: str
    node_results: Mapping[str, TrainingResult]
    cross_fit_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchPlugin:
    id: str
    data_sources: tuple[DataSource, ...]
    feature_computers: tuple[FeatureComputer, ...]
    feature_sets: tuple[FeatureSetSpec, ...]
    objectives: tuple[ObjectiveSpec, ...]
    metrics: tuple[Metric, ...]
    model_specs: tuple[ModelSpec, ...]
    model_runners: tuple[ModelRunner, ...]
    model_pools: tuple[Any, ...] = ()
    calibrators: tuple[Any, ...] = ()
    split_strategies: tuple[Any, ...] = ()
    research_spaces: tuple[Any, ...] = ()
    model_trainers: tuple[ModelTrainer, ...] = ()
    evaluators: tuple[Evaluator, ...] = ()
    model_graphs: tuple[ModelGraphSpec, ...] = ()
    services: Mapping[str, Any] = field(default_factory=dict)
