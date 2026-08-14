"""Decision evaluation that never fits or mutates model state."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from automo.contracts import DecisionOutcome, DecisionPolicy, load_decision_policy


class DecisionError(RuntimeError):
    """Raised when a run cannot produce an immutable decision."""


@dataclass(frozen=True)
class ExperimentDecision:
    run_id: str
    outcome: DecisionOutcome
    decision_path: Path
    reasons: tuple[str, ...]


def decide_local_run(root: Path, run_id: str) -> ExperimentDecision:
    """Create exactly one decision from existing validation and OOS evidence."""
    root = root.resolve()
    run_directory = root / "runs" / run_id
    decision_path = run_directory / "decision.json"
    if decision_path.exists():
        raise DecisionError(f"decision already exists and is immutable: {decision_path}")

    manifest_path = run_directory / "manifest.json"
    validation_path = run_directory / "validation.json"
    oos_path = run_directory / "out-of-sample.json"
    evidence_paths = (manifest_path, validation_path, oos_path)
    if any(not path.exists() for path in evidence_paths):
        missing = [path.name for path in evidence_paths if not path.exists()]
        raise DecisionError("completed run evidence is missing: " + ", ".join(missing))

    manifest = _read_mapping(manifest_path)
    policy_id = _policy_id(manifest)
    policy_path = root / "research" / "policies" / f"{policy_id}.yaml"
    try:
        policy = load_decision_policy(policy_path)
    except (OSError, ValueError) as exc:
        raise DecisionError(f"invalid decision policy: {policy_path}: {exc}") from exc
    if policy.identifier != policy_id:
        raise DecisionError("decision policy id does not match its filename reference")

    validation = _read_mapping(validation_path)
    oos = _read_mapping(oos_path)
    outcome, reasons, diagnostics = _evaluate(policy, validation, oos)
    payload: dict[str, object] = {
        "artifact_type": "automo.experiment_decision",
        "schema_version": 1,
        "run_id": run_id,
        "experiment_id": manifest.get("experiment_id"),
        "created_at": datetime.now(UTC).isoformat(),
        "outcome": outcome.value,
        "policy": {
            "id": policy.identifier,
            "path": str(policy_path.relative_to(root)),
            "sha256": _sha256(policy_path),
            "contract": asdict(policy),
        },
        "evidence": {
            "manifest": {"path": manifest_path.name, "sha256": _sha256(manifest_path)},
            "validation": {"path": validation_path.name, "sha256": _sha256(validation_path)},
            "out_of_sample": {"path": oos_path.name, "sha256": _sha256(oos_path)},
        },
        "diagnostics": diagnostics,
        "reasons": list(reasons),
        "refit_performed": False,
    }
    decision_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ExperimentDecision(run_id, outcome, decision_path, reasons)


def _evaluate(
    policy: DecisionPolicy, validation: dict[str, Any], oos: dict[str, Any]
) -> tuple[DecisionOutcome, tuple[str, ...], dict[str, object]]:
    required = ("observations", "baseline_mse", "candidate_mse", "candidate_delta")
    missing = [f"validation.{key}" for key in required if key not in validation]
    missing.extend(f"out_of_sample.{key}" for key in required if key not in oos)
    if missing:
        return DecisionOutcome.INVALID, ("required evidence fields are missing",), {"missing": missing}
    try:
        val_n = int(validation["observations"])
        oos_n = int(oos["observations"])
        val_delta = float(validation["candidate_delta"])
        oos_delta = float(oos["candidate_delta"])
    except (TypeError, ValueError):
        return DecisionOutcome.INVALID, ("metric evidence contains non-numeric values",), {}
    values = (
        validation["baseline_mse"], validation["candidate_mse"], validation["candidate_delta"],
        oos["baseline_mse"], oos["candidate_mse"], oos["candidate_delta"],
    )
    try:
        if any(not _finite(float(value)) for value in values):
            return DecisionOutcome.INVALID, ("metric evidence contains non-finite values",), {}
    except (TypeError, ValueError):
        return DecisionOutcome.INVALID, ("metric evidence contains non-numeric values",), {}

    val_improvement = -val_delta if policy.lower_is_better else val_delta
    oos_improvement = -oos_delta if policy.lower_is_better else oos_delta
    degradation = max(0.0, val_improvement - oos_improvement)
    diagnostics: dict[str, object] = {
        "validation_observations": val_n,
        "out_of_sample_observations": oos_n,
        "validation_improvement": val_improvement,
        "out_of_sample_improvement": oos_improvement,
        "oos_degradation_from_validation": degradation,
    }
    if val_n < policy.minimum_validation_observations or oos_n < policy.minimum_out_of_sample_observations:
        return DecisionOutcome.INCONCLUSIVE, ("insufficient observations for the committed policy",), diagnostics

    directional_agreement = (val_improvement > 0) == (oos_improvement > 0)
    diagnostics["directional_agreement"] = directional_agreement
    failures: list[str] = []
    if val_improvement < policy.minimum_validation_improvement:
        failures.append("validation improvement did not meet the committed threshold")
    if oos_improvement < policy.minimum_out_of_sample_improvement:
        failures.append("out-of-sample improvement did not meet the committed threshold")
    if degradation > policy.maximum_oos_degradation_from_validation:
        failures.append("out-of-sample degradation exceeded the committed threshold")
    if policy.require_directional_agreement and not directional_agreement:
        failures.append("validation and out-of-sample directions disagree")
    if failures:
        return DecisionOutcome.REJECTED, tuple(failures), diagnostics
    return DecisionOutcome.ACCEPTED, ("all committed decision-policy gates passed",), diagnostics


def _policy_id(manifest: dict[str, Any]) -> str:
    value = manifest.get("decision_policy")
    if isinstance(value, str) and value:
        return value
    model = manifest.get("model")
    if isinstance(model, dict):
        value = model.get("decision_policy")
        if isinstance(value, str) and value:
            return value
    raise DecisionError("manifest does not reference a decision policy")


def _read_mapping(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DecisionError(f"invalid JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise DecisionError(f"evidence must be a mapping: {path}")
    return value


def _finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
