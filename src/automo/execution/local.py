"""Deterministic local fitting runner with a sealed out-of-sample gate."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from automo.contracts import ExperimentSpec


class ExecutionError(RuntimeError):
    """Raised when a committed experiment cannot be executed safely."""


@dataclass(frozen=True)
class Observation:
    timestamp: str
    entity_id: str
    target: float
    feature_1: float


@dataclass(frozen=True)
class FittedLinearModel:
    intercept: float
    coefficient: float

    def predict(self, value: float) -> float:
        return self.intercept + self.coefficient * value


@dataclass(frozen=True)
class MetricEvidence:
    observations: int
    baseline_mse: float
    candidate_mse: float
    candidate_delta: float


@dataclass(frozen=True)
class PreparedExperimentResult:
    run_id: str
    run_directory: Path
    freeze_path: Path
    validation_path: Path
    configuration_fingerprint: str


@dataclass(frozen=True)
class ExperimentRunResult:
    run_id: str
    run_directory: Path
    manifest_path: Path
    freeze_path: Path
    validation_path: Path
    out_of_sample_path: Path
    configuration_fingerprint: str


def prepare_local_experiment(
    root: Path,
    experiment: ExperimentSpec,
    *,
    seed: int = 42,
    run_id: str | None = None,
) -> PreparedExperimentResult:
    """Fit and validate a candidate, then persist its immutable freeze contract."""
    _validate_supported_contract(experiment)
    root = root.resolve()
    data_path = root / "data" / "local-fixture.csv"
    rows = _load_fixture(data_path)
    training, validation, out_of_sample = _temporal_split(rows)
    if not training or not validation or not out_of_sample:
        raise ExecutionError("fixture must contain non-empty training, validation, and OOS splits")

    experiment_path = root / "research" / "experiments" / f"{experiment.identifier}.yaml"
    source_path = Path(__file__).resolve()
    fingerprint = _configuration_fingerprint(experiment_path, data_path, source_path, seed)
    resolved_run_id = run_id or _default_run_id(experiment.identifier, fingerprint)
    run_directory = root / "runs" / resolved_run_id
    if run_directory.exists():
        raise ExecutionError(f"run directory already exists and is immutable: {run_directory}")
    run_directory.mkdir(parents=True)

    started = time.perf_counter()
    baseline_mean = sum(row.target for row in training) / len(training)
    candidate = _fit_linear(training)
    validation_evidence = _evaluate(validation, baseline_mean, candidate)
    duration_ms = round((time.perf_counter() - started) * 1000, 3)

    validation_path = run_directory / "validation.json"
    freeze_path = run_directory / "freeze.json"
    _write_json(validation_path, {"artifact_type": "automo.validation_evidence", "schema_version": 1, "stage": "validation", **asdict(validation_evidence)})
    freeze = {
        "artifact_type": "automo.freeze_contract",
        "schema_version": 1,
        "run_id": resolved_run_id,
        "experiment_id": experiment.identifier,
        "frozen_at": datetime.now(UTC).isoformat(),
        "configuration_fingerprint": fingerprint,
        "seed": seed,
        "inputs": {
            "runner_sha256": _sha256(source_path),
            "experiment_path": str(experiment_path.relative_to(root)),
            "experiment_sha256": _sha256(experiment_path),
            "data_path": str(data_path.relative_to(root)),
            "data_sha256": _sha256(data_path),
            "split_spec": experiment.split_spec,
            "baseline": experiment.baseline,
            "candidate_model": experiment.candidate_model,
            "feature_set": experiment.feature_set,
            "decision_policy": experiment.decision_policy,
        },
        "split": {
            "training": len(training),
            "validation": len(validation),
            "out_of_sample": len(out_of_sample),
        },
        "fitted_state": {
            "baseline_mean": baseline_mean,
            "candidate": asdict(candidate),
        },
        "validation": {
            "path": validation_path.name,
            "sha256": _sha256(validation_path),
        },
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "duration_ms": duration_ms,
        "compute_cost": 0.0,
        "status": "frozen",
    }
    _write_json(freeze_path, freeze)
    return PreparedExperimentResult(
        run_id=resolved_run_id,
        run_directory=run_directory,
        freeze_path=freeze_path,
        validation_path=validation_path,
        configuration_fingerprint=fingerprint,
    )


def evaluate_local_out_of_sample(root: Path, run_id: str) -> ExperimentRunResult:
    """Verify the frozen inputs, then evaluate the untouched OOS partition once."""
    root = root.resolve()
    run_directory = root / "runs" / run_id
    freeze_path = run_directory / "freeze.json"
    if not freeze_path.exists():
        raise ExecutionError(f"OOS evaluation requires a valid freeze artifact: {freeze_path}")
    out_of_sample_path = run_directory / "out-of-sample.json"
    manifest_path = run_directory / "manifest.json"
    if out_of_sample_path.exists() or manifest_path.exists():
        raise ExecutionError(f"OOS evidence already exists and is immutable: {run_directory}")

    freeze = _read_json(freeze_path)
    _verify_frozen_inputs(root, freeze)
    data_path = root / str(freeze["inputs"]["data_path"])
    rows = _load_fixture(data_path)
    _, _, out_of_sample = _temporal_split(rows)
    if not out_of_sample:
        raise ExecutionError("fixture must contain a non-empty OOS split")

    fitted_state = freeze["fitted_state"]
    candidate_values = fitted_state["candidate"]
    candidate = FittedLinearModel(
        intercept=float(candidate_values["intercept"]),
        coefficient=float(candidate_values["coefficient"]),
    )
    started = time.perf_counter()
    evidence = _evaluate(out_of_sample, float(fitted_state["baseline_mean"]), candidate)
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    _write_json(out_of_sample_path, {"artifact_type": "automo.out_of_sample_evidence", "schema_version": 1, "stage": "out-of-sample", **asdict(evidence)})

    manifest = {
        "artifact_type": "automo.run_manifest",
        "schema_version": 2,
        "run_id": run_id,
        "experiment_id": freeze["experiment_id"],
        "created_at": datetime.now(UTC).isoformat(),
        "configuration_fingerprint": freeze["configuration_fingerprint"],
        "seed": freeze["seed"],
        "code": {
            "runner_sha256": freeze["inputs"]["runner_sha256"],
            "experiment_sha256": freeze["inputs"]["experiment_sha256"],
        },
        "data": {
            "snapshot_path": freeze["inputs"]["data_path"],
            "snapshot_sha256": freeze["inputs"]["data_sha256"],
            "observations": sum(int(value) for value in freeze["split"].values()),
        },
        "environment": freeze["environment"],
        "split": {**freeze["split"], "protocol": freeze["inputs"]["split_spec"]},
        "model": {
            "baseline": freeze["inputs"]["baseline"],
            "candidate": freeze["inputs"]["candidate_model"],
            "feature_set": freeze["inputs"]["feature_set"],
            "decision_policy": freeze["inputs"]["decision_policy"],
            "fitted_parameters": freeze["fitted_state"]["candidate"],
            "baseline_mean": freeze["fitted_state"]["baseline_mean"],
        },
        "freeze": {"path": freeze_path.name, "sha256": _sha256(freeze_path)},
        "evidence": {
            "validation": freeze["validation"]["path"],
            "out_of_sample": out_of_sample_path.name,
        },
        "duration_ms": round(float(freeze["duration_ms"]) + duration_ms, 3),
        "compute_cost": float(freeze["compute_cost"]),
    }
    _write_json(manifest_path, manifest)
    return ExperimentRunResult(
        run_id=run_id,
        run_directory=run_directory,
        manifest_path=manifest_path,
        freeze_path=freeze_path,
        validation_path=run_directory / str(freeze["validation"]["path"]),
        out_of_sample_path=out_of_sample_path,
        configuration_fingerprint=str(freeze["configuration_fingerprint"]),
    )


def run_local_experiment(
    root: Path,
    experiment: ExperimentSpec,
    *,
    seed: int = 42,
    run_id: str | None = None,
) -> ExperimentRunResult:
    """Compatibility helper that prepares, freezes, and then evaluates OOS."""
    prepared = prepare_local_experiment(root, experiment, seed=seed, run_id=run_id)
    return evaluate_local_out_of_sample(root, prepared.run_id)


def _verify_frozen_inputs(root: Path, freeze: dict[str, object]) -> None:
    inputs = freeze.get("inputs")
    if not isinstance(inputs, dict):
        raise ExecutionError("freeze artifact is invalid: inputs must be a mapping")
    checks = {
        "experiment": (root / str(inputs["experiment_path"]), str(inputs["experiment_sha256"])),
        "dataset": (root / str(inputs["data_path"]), str(inputs["data_sha256"])),
        "runner": (Path(__file__).resolve(), str(inputs["runner_sha256"])),
    }
    changed = [name for name, (path, expected) in checks.items() if not path.exists() or _sha256(path) != expected]
    if changed:
        raise ExecutionError("post-freeze configuration change detected: " + ", ".join(changed))
    validation = freeze.get("validation")
    if not isinstance(validation, dict):
        raise ExecutionError("freeze artifact is invalid: validation must be a mapping")
    validation_path = root / "runs" / str(freeze["run_id"]) / str(validation["path"])
    if not validation_path.exists() or _sha256(validation_path) != str(validation["sha256"]):
        raise ExecutionError("post-freeze validation evidence change detected")


def _validate_supported_contract(experiment: ExperimentSpec) -> None:
    expected = {
        "baseline": "BASELINE-NAIVE-0001",
        "candidate": "MODEL-LINEAR-0001",
        "features": "FEATURESET-CORE-0001",
        "split": "SPLIT-WALK-FORWARD-0001",
    }
    actual = {
        "baseline": experiment.baseline,
        "candidate": experiment.candidate_model,
        "features": experiment.feature_set,
        "split": experiment.split_spec,
    }
    unsupported = [key for key, value in actual.items() if value != expected[key]]
    if unsupported:
        raise ExecutionError("local runner does not support contract fields: " + ", ".join(unsupported))


def _load_fixture(path: Path) -> tuple[Observation, ...]:
    if not path.exists():
        raise ExecutionError(f"local fixture is unavailable: {path}")
    rows: list[Observation] = []
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        required = {"timestamp", "entity_id", "target", "feature_1"}
        if set(reader.fieldnames or ()) != required:
            raise ExecutionError(f"fixture fields must be exactly: {', '.join(sorted(required))}")
        for item in reader:
            rows.append(
                Observation(
                    timestamp=item["timestamp"],
                    entity_id=item["entity_id"],
                    target=float(item["target"]),
                    feature_1=float(item["feature_1"]),
                )
            )
    return tuple(sorted(rows, key=lambda row: (row.timestamp, row.entity_id)))


def _temporal_split(
    rows: Iterable[Observation],
) -> tuple[tuple[Observation, ...], tuple[Observation, ...], tuple[Observation, ...]]:
    training: list[Observation] = []
    validation: list[Observation] = []
    out_of_sample: list[Observation] = []
    for row in rows:
        year = int(row.timestamp[:4])
        if year <= 2022:
            training.append(row)
        elif year == 2023:
            validation.append(row)
        elif year == 2024:
            out_of_sample.append(row)
    return tuple(training), tuple(validation), tuple(out_of_sample)


def _fit_linear(rows: tuple[Observation, ...]) -> FittedLinearModel:
    mean_x = sum(row.feature_1 for row in rows) / len(rows)
    mean_y = sum(row.target for row in rows) / len(rows)
    denominator = sum((row.feature_1 - mean_x) ** 2 for row in rows)
    if denominator == 0:
        raise ExecutionError("candidate cannot fit a constant feature")
    coefficient = sum(
        (row.feature_1 - mean_x) * (row.target - mean_y) for row in rows
    ) / denominator
    return FittedLinearModel(mean_y - coefficient * mean_x, coefficient)


def _evaluate(
    rows: tuple[Observation, ...],
    baseline_mean: float,
    candidate: FittedLinearModel,
) -> MetricEvidence:
    baseline_mse = sum((row.target - baseline_mean) ** 2 for row in rows) / len(rows)
    candidate_mse = sum(
        (row.target - candidate.predict(row.feature_1)) ** 2 for row in rows
    ) / len(rows)
    return MetricEvidence(
        observations=len(rows),
        baseline_mse=round(baseline_mse, 12),
        candidate_mse=round(candidate_mse, 12),
        candidate_delta=round(candidate_mse - baseline_mse, 12),
    )


def _configuration_fingerprint(*paths_and_seed: object) -> str:
    digest = hashlib.sha256()
    for value in paths_and_seed:
        if isinstance(value, Path):
            digest.update(value.read_bytes())
        else:
            digest.update(str(value).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _default_run_id(experiment_id: str, fingerprint: str) -> str:
    return f"{experiment_id.lower()}-{fingerprint[:12]}"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExecutionError(f"invalid freeze artifact: {path}") from exc
    if not isinstance(value, dict):
        raise ExecutionError(f"invalid freeze artifact: {path}")
    return value
