from __future__ import annotations

import hashlib
from dataclasses import fields
from pathlib import Path
from typing import Any, Iterable

from automo.persistence import read_yaml_artifact, write_yaml_artifact

from .contracts import (
    BenchmarkObservation,
    CalibrationArtifactCodec,
    CalibrationManifest,
    LifecycleEvent,
    ModelArtifactCodec,
    ModelManifest,
    ModelRecord,
    ModelStatus,
    TrainingProvenance,
    transition_allowed,
)


class RegistryError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_yaml(path: Path, *, artifact_type: str) -> dict[str, Any]:
    return read_yaml_artifact(path, artifact_type=artifact_type)


def _atomic_yaml(path: Path, payload: dict[str, Any], *, artifact_type: str) -> None:
    write_yaml_artifact(path, artifact_type=artifact_type, payload=payload)

def _next_id(paths: Iterable[Path], prefix: str) -> str:
    largest = 0
    for path in paths:
        name = path.stem if path.is_file() else path.name
        if name.startswith(prefix + "-"):
            try:
                largest = max(largest, int(name.rsplit("-", 1)[1]))
            except ValueError:
                continue
    return f"{prefix}-{largest + 1:06d}"


def _dataclass_from_mapping(cls: Any, raw: dict[str, Any]) -> Any:
    accepted = {item.name for item in fields(cls)}
    return cls(**{key: value for key, value in raw.items() if key in accepted})


class FilesystemModelRegistry:
    """Git-friendly local model registry with immutable identity documents."""

    def __init__(
        self,
        root: Path,
        *,
        codecs: Iterable[ModelArtifactCodec] = (),
        calibration_codecs: Iterable[CalibrationArtifactCodec] = (),
    ) -> None:
        self.root = root
        self.models_root = root / "models"
        self.calibrations_root = root / "calibrations"
        self.benchmarks_root = root / "benchmarks"
        self.events_root = root / "events"
        self.codecs = {codec.id: codec for codec in codecs}
        self.calibration_codecs = {codec.id: codec for codec in calibration_codecs}
        for path in (self.models_root, self.calibrations_root, self.benchmarks_root, self.events_root):
            path.mkdir(parents=True, exist_ok=True)

    def register_codec(self, codec: ModelArtifactCodec) -> None:
        self.codecs[codec.id] = codec

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
    ) -> ModelManifest:
        model_id = model_id or _next_id(self.models_root.iterdir(), "MODEL")
        model_dir = self.models_root / model_id
        if model_dir.exists():
            raise RegistryError(f"model already exists: {model_id}")
        model_dir.mkdir(parents=True)
        artifact_dir = model_dir / "artifact"
        artifact_dir.mkdir()
        artifact_path = artifact_dir / "model.bin"
        try:
            codec.save(model, artifact_path)
            provenance_path = model_dir / "provenance.yaml"
            _atomic_yaml(provenance_path, provenance.as_dict(), artifact_type="automo.training_provenance")
            manifest = ModelManifest(
                id=model_id,
                implementation=implementation,
                model_spec_id=model_spec_id,
                objective_id=objective_id,
                feature_set_id=feature_set_id,
                artifact_codec=codec.id,
                artifact_path=str(artifact_path.relative_to(self.root)),
                artifact_hash=_sha256(artifact_path),
                provenance_path=str(provenance_path.relative_to(self.root)),
                parent_model_id=parent_model_id,
            )
            _atomic_yaml(model_dir / "manifest.yaml", manifest.as_dict(), artifact_type="automo.model_manifest")
            self.codecs[codec.id] = codec
            self._write_initial_event(model_id)
            return manifest
        except Exception:
            import shutil
            shutil.rmtree(model_dir, ignore_errors=True)
            raise

    def _write_initial_event(self, model_id: str) -> None:
        event_dir = self.events_root / model_id
        event_dir.mkdir(parents=True, exist_ok=True)
        event = LifecycleEvent(
            id="EVENT-000001",
            model_id=model_id,
            from_status=None,
            to_status=ModelStatus.CANDIDATE,
            reason="model registered",
        )
        _atomic_yaml(event_dir / f"{event.id}.yaml", event.as_dict(), artifact_type="automo.lifecycle_event")

    def get_manifest(self, model_id: str) -> ModelManifest:
        path = self.models_root / model_id / "manifest.yaml"
        if not path.is_file():
            raise RegistryError(f"unknown model: {model_id}")
        return _dataclass_from_mapping(ModelManifest, _read_yaml(path, artifact_type="automo.model_manifest"))

    def get_provenance(self, model_id: str) -> TrainingProvenance:
        manifest = self.get_manifest(model_id)
        return _dataclass_from_mapping(TrainingProvenance, _read_yaml(self.root / manifest.provenance_path, artifact_type="automo.training_provenance"))

    def load_model(self, model_id: str) -> Any:
        manifest = self.get_manifest(model_id)
        try:
            codec = self.codecs[manifest.artifact_codec]
        except KeyError as exc:
            raise RegistryError(f"artifact codec is not registered: {manifest.artifact_codec}") from exc
        path = self.root / manifest.artifact_path
        if _sha256(path) != manifest.artifact_hash:
            raise RegistryError(f"model artifact hash mismatch: {model_id}")
        return codec.load(path)

    def status(self, model_id: str) -> ModelStatus:
        events = self.history(model_id)
        if not events:
            raise RegistryError(f"model has no lifecycle history: {model_id}")
        return events[-1].to_status

    def transition(self, model_id: str, target: ModelStatus, *, reason: str) -> LifecycleEvent:
        self.get_manifest(model_id)
        current = self.status(model_id)
        if not transition_allowed(current, target):
            raise RegistryError(f"illegal lifecycle transition: {current.value} -> {target.value}")
        event_dir = self.events_root / model_id
        event = LifecycleEvent(
            id=_next_id(event_dir.iterdir(), "EVENT"),
            model_id=model_id,
            from_status=current,
            to_status=target,
            reason=reason,
        )
        _atomic_yaml(event_dir / f"{event.id}.yaml", event.as_dict(), artifact_type="automo.lifecycle_event")
        return event

    def history(self, model_id: str) -> tuple[LifecycleEvent, ...]:
        event_dir = self.events_root / model_id
        if not event_dir.is_dir():
            return ()
        events: list[LifecycleEvent] = []
        for path in sorted(event_dir.glob("EVENT-*.yaml")):
            raw = _read_yaml(path, artifact_type="automo.lifecycle_event")
            raw["from_status"] = ModelStatus(raw["from_status"]) if raw.get("from_status") else None
            raw["to_status"] = ModelStatus(raw["to_status"])
            events.append(_dataclass_from_mapping(LifecycleEvent, raw))
        return tuple(events)

    def add_benchmark(self, observation: BenchmarkObservation) -> BenchmarkObservation:
        self.get_manifest(observation.model_id)
        model_root = self.benchmarks_root / observation.model_id
        model_root.mkdir(parents=True, exist_ok=True)
        if (model_root / f"{observation.id}.yaml").exists():
            raise RegistryError(f"benchmark already exists: {observation.id}")
        _atomic_yaml(model_root / f"{observation.id}.yaml", observation.as_dict(), artifact_type="automo.benchmark_observation")
        return observation

    def append_benchmark(
        self,
        model_id: str,
        *,
        metric_id: str,
        direction: Any,
        scope: Any,
        value: float,
        sample_count: int,
        split: str,
        evidence_cutoff: str | None = None,
        regime: dict[str, str] | None = None,
        calibration_id: str | None = None,
    ) -> BenchmarkObservation:
        model_root = self.benchmarks_root / model_id
        model_root.mkdir(parents=True, exist_ok=True)
        observation = BenchmarkObservation(
            id=_next_id(model_root.iterdir(), "BENCHMARK"),
            model_id=model_id,
            metric_id=metric_id,
            direction=getattr(direction, "value", str(direction)),
            scope=getattr(scope, "value", str(scope)),
            value=float(value),
            sample_count=int(sample_count),
            split=split,
            evidence_cutoff=evidence_cutoff,
            regime=regime or {},
            calibration_id=calibration_id,
        )
        return self.add_benchmark(observation)

    def benchmarks(self, model_id: str) -> tuple[BenchmarkObservation, ...]:
        root = self.benchmarks_root / model_id
        if not root.is_dir():
            return ()
        values: list[BenchmarkObservation] = []
        for path in sorted(root.glob("BENCHMARK-*.yaml")):
            raw = _read_yaml(path, artifact_type="automo.benchmark_observation")
            values.append(_dataclass_from_mapping(BenchmarkObservation, raw))
        return tuple(values)

    def register_calibration(
        self,
        base_model_id: str,
        calibration: Any,
        *,
        implementation: str,
        codec: CalibrationArtifactCodec,
        calibration_data_snapshot_id: str,
        calibration_data_snapshot_hash: str | None = None,
        window_start: str | None = None,
        window_end: str | None = None,
        calibration_id: str | None = None,
    ) -> CalibrationManifest:
        self.get_manifest(base_model_id)
        calibration_id = calibration_id or _next_id(self.calibrations_root.iterdir(), "CALIBRATION")
        directory = self.calibrations_root / calibration_id
        if directory.exists():
            raise RegistryError(f"calibration already exists: {calibration_id}")
        directory.mkdir(parents=True)
        artifact = directory / "artifact.bin"
        try:
            codec.save(calibration, artifact)
            manifest = CalibrationManifest(
                id=calibration_id,
                base_model_id=base_model_id,
                implementation=implementation,
                artifact_codec=codec.id,
                artifact_path=str(artifact.relative_to(self.root)),
                artifact_hash=_sha256(artifact),
                calibration_data_snapshot_id=calibration_data_snapshot_id,
                calibration_data_snapshot_hash=calibration_data_snapshot_hash,
                window_start=window_start,
                window_end=window_end,
            )
            _atomic_yaml(directory / "manifest.yaml", manifest.as_dict(), artifact_type="automo.calibration_manifest")
            self.calibration_codecs[codec.id] = codec
            return manifest
        except Exception:
            import shutil
            shutil.rmtree(directory, ignore_errors=True)
            raise


    def load_calibration(self, calibration_id: str) -> Any:
        path = self.calibrations_root / calibration_id / "manifest.yaml"
        if not path.is_file():
            raise RegistryError(f"unknown calibration: {calibration_id}")
        manifest = _dataclass_from_mapping(CalibrationManifest, _read_yaml(path, artifact_type="automo.calibration_manifest"))
        try:
            codec = self.calibration_codecs[manifest.artifact_codec]
        except KeyError as exc:
            raise RegistryError(f"calibration codec is not registered: {manifest.artifact_codec}") from exc
        artifact = self.root / manifest.artifact_path
        if _sha256(artifact) != manifest.artifact_hash:
            raise RegistryError(f"calibration artifact hash mismatch: {calibration_id}")
        return codec.load(artifact)

    def calibrations(self, model_id: str) -> tuple[CalibrationManifest, ...]:
        values: list[CalibrationManifest] = []
        for path in sorted(self.calibrations_root.glob("CALIBRATION-*/manifest.yaml")):
            raw = _read_yaml(path, artifact_type="automo.calibration_manifest")
            if raw.get("base_model_id") == model_id:
                values.append(_dataclass_from_mapping(CalibrationManifest, raw))
        return tuple(values)

    def get_record(self, model_id: str) -> ModelRecord:
        benchmarks = self.benchmarks(model_id)
        latest: dict[str, BenchmarkObservation] = {}
        for item in benchmarks:
            latest[item.metric_id] = item
        calibrations = self.calibrations(model_id)
        return ModelRecord(
            manifest=self.get_manifest(model_id),
            provenance=self.get_provenance(model_id),
            status=self.status(model_id),
            latest_benchmarks=latest,
            latest_calibration=calibrations[-1] if calibrations else None,
        )

    def list_models(self, *, status: ModelStatus | None = None) -> tuple[ModelRecord, ...]:
        records: list[ModelRecord] = []
        for path in sorted(self.models_root.glob("MODEL-*")):
            if not path.is_dir():
                continue
            record = self.get_record(path.name)
            if status is None or record.status == status:
                records.append(record)
        return tuple(records)
