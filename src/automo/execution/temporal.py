"""Bounded predefined temporal-fold evaluation for the local fixture."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from automo.contracts import ExperimentSpec
from automo.execution.local import (
    ExecutionError,
    _evaluate,
    _fit_linear,
    _load_fixture,
    _sha256,
)


@dataclass(frozen=True)
class TemporalFold:
    identifier: str
    training_end_year: int
    validation_year: int
    out_of_sample_year: int


@dataclass(frozen=True)
class TemporalStabilityResult:
    run_id: str
    run_directory: Path
    evidence_path: Path
    fold_count: int
    configuration_fingerprint: str


PREDEFINED_FOLDS = (
    TemporalFold("FOLD-001", 2020, 2021, 2022),
    TemporalFold("FOLD-002", 2021, 2022, 2023),
    TemporalFold("FOLD-003", 2022, 2023, 2024),
)


def run_temporal_stability(
    root: Path,
    experiment: ExperimentSpec,
    *,
    run_id: str | None = None,
) -> TemporalStabilityResult:
    """Execute only the committed predefined folds within the experiment budget."""
    if experiment.split_spec != "SPLIT-PREDEFINED-TEMPORAL-FOLDS-0001":
        raise ExecutionError(f"unsupported temporal split specification: {experiment.split_spec}")
    if experiment.evaluation_spec != "EVALUATION-TEMPORAL-STABILITY-0001":
        raise ExecutionError(f"unsupported temporal evaluation specification: {experiment.evaluation_spec}")
    if experiment.maximum_trials < len(PREDEFINED_FOLDS):
        raise ExecutionError(
            f"experiment trial budget {experiment.maximum_trials} is below committed fold count {len(PREDEFINED_FOLDS)}"
        )

    root = root.resolve()
    experiment_path = root / "research" / "experiments" / f"{experiment.identifier}.yaml"
    data_path = root / "data" / "local-fixture.csv"
    rows = _load_fixture(data_path)
    fingerprint = _fingerprint(experiment_path, data_path)
    resolved_run_id = run_id or f"{experiment.identifier.lower()}-stability-{fingerprint[:12]}"
    run_directory = root / "runs" / resolved_run_id
    if run_directory.exists():
        raise ExecutionError(f"run directory already exists and is immutable: {run_directory}")
    run_directory.mkdir(parents=True)

    fold_payloads: list[dict[str, object]] = []
    for order, fold in enumerate(PREDEFINED_FOLDS, start=1):
        training = tuple(row for row in rows if int(row.timestamp[:4]) <= fold.training_end_year)
        validation = tuple(row for row in rows if int(row.timestamp[:4]) == fold.validation_year)
        out_of_sample = tuple(row for row in rows if int(row.timestamp[:4]) == fold.out_of_sample_year)
        if not training or not validation or not out_of_sample:
            raise ExecutionError(f"fixture cannot satisfy committed fold {fold.identifier}")
        baseline_mean = sum(row.target for row in training) / len(training)
        candidate = _fit_linear(training)
        validation_evidence = _evaluate(validation, baseline_mean, candidate)
        oos_evidence = _evaluate(out_of_sample, baseline_mean, candidate)
        fold_payloads.append(
            {
                "order": order,
                "fold_id": fold.identifier,
                "training_end_year": fold.training_end_year,
                "validation_year": fold.validation_year,
                "out_of_sample_year": fold.out_of_sample_year,
                "training_observations": len(training),
                "validation": asdict(validation_evidence),
                "out_of_sample": asdict(oos_evidence),
            }
        )

    validation_deltas = [float(item["validation"]["candidate_delta"]) for item in fold_payloads]  # type: ignore[index]
    oos_deltas = [float(item["out_of_sample"]["candidate_delta"]) for item in fold_payloads]  # type: ignore[index]
    payload = {
        "artifact_type": "automo.temporal_stability",
        "schema_version": 1,
        "run_id": resolved_run_id,
        "experiment_id": experiment.identifier,
        "configuration_fingerprint": fingerprint,
        "trial_budget": experiment.maximum_trials,
        "trials_executed": len(fold_payloads),
        "trial_order": [fold.identifier for fold in PREDEFINED_FOLDS],
        "committed_folds_only": True,
        "inputs": {
            "experiment_path": str(experiment_path.relative_to(root)),
            "experiment_sha256": _sha256(experiment_path),
            "data_path": str(data_path.relative_to(root)),
            "data_sha256": _sha256(data_path),
            "split_spec": experiment.split_spec,
            "evaluation_spec": experiment.evaluation_spec,
            "candidate_model": experiment.candidate_model,
            "feature_set": experiment.feature_set,
        },
        "folds": fold_payloads,
        "aggregate": {
            "mean_validation_delta": round(sum(validation_deltas) / len(validation_deltas), 12),
            "mean_out_of_sample_delta": round(sum(oos_deltas) / len(oos_deltas), 12),
            "validation_improved_folds": sum(delta < 0 for delta in validation_deltas),
            "out_of_sample_improved_folds": sum(delta < 0 for delta in oos_deltas),
            "directional_agreement": all(
                (validation < 0 and oos < 0) or (validation >= 0 and oos >= 0)
                for validation, oos in zip(validation_deltas, oos_deltas, strict=True)
            ),
        },
        "refit_scope": "once per committed fold using training rows only",
        "arbitrary_trial_search": False,
        "compute_cost": 0.0,
    }
    evidence_path = run_directory / "temporal-stability.json"
    evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return TemporalStabilityResult(
        run_id=resolved_run_id,
        run_directory=run_directory,
        evidence_path=evidence_path,
        fold_count=len(fold_payloads),
        configuration_fingerprint=fingerprint,
    )


def _fingerprint(*paths: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.read_bytes())
        digest.update(b"\0")
    digest.update("|".join(fold.identifier for fold in PREDEFINED_FOLDS).encode())
    return digest.hexdigest()
