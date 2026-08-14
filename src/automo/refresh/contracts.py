from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Protocol, Sequence

from automo.runtime.contracts import DataSnapshot, MetricDirection, ModelSpec


class RefreshError(RuntimeError):
    pass


@dataclass(frozen=True)
class DataPartition:
    id: str
    row_indices: tuple[int, ...]


@dataclass(frozen=True)
class EvaluationPartitions:
    fit: DataPartition
    validation: DataPartition
    test: DataPartition

    def __post_init__(self) -> None:
        groups = (set(self.fit.row_indices), set(self.validation.row_indices), set(self.test.row_indices))
        if groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2]:
            raise ValueError("fit, validation and test partitions must be disjoint")


class SplitStrategy(Protocol):
    id: str
    def split(self, snapshot: DataSnapshot) -> EvaluationPartitions: ...


@dataclass(frozen=True)
class DataIteration:
    id: str
    snapshot_id: str
    snapshot_hash: str | None
    previous_iteration_id: str | None = None
    delta_partition: DataPartition | None = None


@dataclass(frozen=True)
class TrainingPolicy:
    id: str
    each_iteration: bool = False
    min_new_observations: int = 0


@dataclass(frozen=True)
class CalibrationPolicy:
    id: str
    each_iteration: bool = False
    min_fit_observations: int = 0
    calibrator: str | None = None


@dataclass(frozen=True)
class RetentionPolicy:
    id: str
    top_k: int = 3
    minimum_test_observations: int = 1
    maximum_validation_test_degradation: float | None = None

    def __post_init__(self) -> None:
        if self.top_k < 1:
            raise ValueError("top_k must be positive")


class SelectionKind(StrEnum):
    BEST_OVERALL = "best_overall"
    RECENT_BEST = "recent_best"


@dataclass(frozen=True)
class SelectionPolicy:
    id: str
    kind: SelectionKind = SelectionKind.BEST_OVERALL
    selector: str | None = None


class ModelSelector(Protocol):
    id: str
    def select(
        self, pool: "ModelPoolSpec", snapshot: "ModelPoolSnapshot", *, context: Mapping[str, Any]
    ) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class ModelPoolSpec:
    id: str
    objective_id: str
    model_spec_id: str | None
    primary_metric_id: str
    primary_metric_direction: MetricDirection
    training_policy: TrainingPolicy
    calibration_policy: CalibrationPolicy
    retention_policy: RetentionPolicy
    selection_policy: SelectionPolicy
    model_spec_ids: tuple[str, ...] = ()

    @property
    def resolved_model_spec_ids(self) -> tuple[str, ...]:
        values = tuple(dict.fromkeys((*(self.model_spec_ids), *((self.model_spec_id,) if self.model_spec_id else ()))))
        if not values:
            raise ValueError("model pool requires at least one model spec id")
        return values


class StructuredCalibrator(Protocol):
    id: str
    artifact_codec: Any
    def fit_outputs(self, outputs: Any, target: Sequence[Any], *, context: Mapping[str, Any]) -> Any: ...


class RefreshAction(StrEnum):
    KEEP = "keep"
    RECALIBRATE = "recalibrate"
    RETRAIN = "retrain"
    DEGRADE = "degrade"
    ARCHIVE = "archive"


@dataclass(frozen=True)
class RefreshScoreCard:
    model_id: str
    calibration_id: str | None
    validation_metrics: Mapping[str, float]
    test_metrics: Mapping[str, float]
    validation_count: int
    test_count: int
    source: str = "existing"


@dataclass(frozen=True)
class ModelRefreshDisposition:
    model_id: str
    action: RefreshAction
    reasons: tuple[str, ...]
    replacement_model_id: str | None = None
    calibration_id: str | None = None


@dataclass(frozen=True)
class ModelPoolSnapshot:
    pool_id: str
    iteration_id: str
    active_model_ids: tuple[str, ...]
    selected_model_ids: tuple[str, ...]
    scorecards: tuple[RefreshScoreCard, ...] = ()


class CalibratorModel(Protocol):
    def transform(self, prediction: Sequence[float]) -> Sequence[float]: ...


class Calibrator(Protocol):
    id: str
    artifact_codec: Any
    def fit(self, prediction: Sequence[float], target: Sequence[float]) -> CalibratorModel: ...
