from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping, Protocol


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModelStatus(StrEnum):
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEGRADED = "degraded"
    ARCHIVED = "archived"
    REJECTED = "rejected"


_ALLOWED_TRANSITIONS: dict[ModelStatus, frozenset[ModelStatus]] = {
    ModelStatus.CANDIDATE: frozenset({ModelStatus.VALIDATED, ModelStatus.REJECTED}),
    ModelStatus.VALIDATED: frozenset({ModelStatus.ACTIVE, ModelStatus.ARCHIVED}),
    ModelStatus.ACTIVE: frozenset({ModelStatus.DEGRADED, ModelStatus.ARCHIVED}),
    ModelStatus.DEGRADED: frozenset({ModelStatus.ACTIVE, ModelStatus.ARCHIVED}),
    ModelStatus.ARCHIVED: frozenset(),
    ModelStatus.REJECTED: frozenset(),
}


def transition_allowed(current: ModelStatus, target: ModelStatus) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]


@dataclass(frozen=True)
class TrainingProvenance:
    data_source_id: str
    data_snapshot_id: str
    data_snapshot_hash: str | None
    feature_set_id: str
    model_spec_id: str
    objective_id: str
    runner_implementation: str
    python_version: str
    seed: int | None = None
    training_window_start: str | None = None
    training_window_end: str | None = None
    code_revision: str | None = None
    environment: Mapping[str, str] = field(default_factory=dict)
    started_at: str | None = None
    completed_at: str = field(default_factory=utc_now_iso)
    model_graph_id: str | None = None
    upstream_model_ids: Mapping[str, str] = field(default_factory=dict)
    upstream_calibration_ids: Mapping[str, str] = field(default_factory=dict)
    cross_fit_protocol: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelManifest:
    id: str
    implementation: str
    model_spec_id: str
    objective_id: str
    feature_set_id: str
    artifact_codec: str
    artifact_path: str
    artifact_hash: str
    provenance_path: str
    created_at: str = field(default_factory=utc_now_iso)
    parent_model_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CalibrationManifest:
    id: str
    base_model_id: str
    implementation: str
    artifact_codec: str
    artifact_path: str
    artifact_hash: str
    calibration_data_snapshot_id: str
    calibration_data_snapshot_hash: str | None = None
    window_start: str | None = None
    window_end: str | None = None
    fitted_at: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkObservation:
    id: str
    model_id: str
    metric_id: str
    direction: str
    scope: str
    value: float
    sample_count: int
    split: str
    evaluated_at: str = field(default_factory=utc_now_iso)
    evidence_cutoff: str | None = None
    regime: Mapping[str, str] = field(default_factory=dict)
    calibration_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["direction"] = self.direction
        payload["scope"] = self.scope
        return payload


@dataclass(frozen=True)
class LifecycleEvent:
    id: str
    model_id: str
    from_status: ModelStatus | None
    to_status: ModelStatus
    reason: str
    at: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["from_status"] = self.from_status.value if self.from_status is not None else None
        payload["to_status"] = self.to_status.value
        return payload


@dataclass(frozen=True)
class ModelRecord:
    manifest: ModelManifest
    provenance: TrainingProvenance
    status: ModelStatus
    latest_benchmarks: Mapping[str, BenchmarkObservation] = field(default_factory=dict)
    latest_calibration: CalibrationManifest | None = None


class ModelArtifactCodec(Protocol):
    id: str

    def save(self, model: Any, path: Path) -> None: ...

    def load(self, path: Path) -> Any: ...


class CalibrationArtifactCodec(Protocol):
    id: str

    def save(self, calibration: Any, path: Path) -> None: ...

    def load(self, path: Path) -> Any: ...


class ModelRegistry(Protocol):
    def register_model(
        self,
        model: Any,
        *,
        implementation: str,
        model_spec_id: str,
        objective_id: str,
        feature_set_id: str,
        provenance: TrainingProvenance,
        codec: ModelArtifactCodec,
        model_id: str | None = None,
        parent_model_id: str | None = None,
    ) -> ModelManifest: ...

    def get_manifest(self, model_id: str) -> ModelManifest: ...
    def get_record(self, model_id: str) -> ModelRecord: ...
    def load_model(self, model_id: str) -> FittedModel: ...
    def list_models(self, *, status: ModelStatus | None = None) -> tuple[ModelRecord, ...]: ...
    def transition(self, model_id: str, target: ModelStatus, *, reason: str) -> LifecycleEvent: ...
    def history(self, model_id: str) -> tuple[LifecycleEvent, ...]: ...
    def add_benchmark(self, observation: BenchmarkObservation) -> BenchmarkObservation: ...
    def benchmarks(self, model_id: str) -> tuple[BenchmarkObservation, ...]: ...
    def register_calibration(self, base_model_id: str, calibration: Any, **kwargs: Any) -> CalibrationManifest: ...
    def calibrations(self, model_id: str) -> tuple[CalibrationManifest, ...]: ...
    def load_calibration(self, calibration_id: str) -> Any: ...
