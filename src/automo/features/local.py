"""Bounded feature-group dispositions from immutable experiment evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from automo.contracts import (
    FeatureDispositionOutcome,
    FeatureDispositionPolicy,
    FeatureGroup,
    load_feature_disposition_policy,
    load_feature_set,
)


class FeatureDispositionError(RuntimeError):
    """Raised when feature evidence cannot be interpreted safely."""


@dataclass(frozen=True)
class FeatureDispositionResult:
    run_id: str
    disposition_path: Path
    outcomes: tuple[tuple[str, FeatureDispositionOutcome], ...]


def dispose_local_features(root: Path, run_id: str) -> FeatureDispositionResult:
    """Create one immutable bounded disposition artifact without changing the run decision."""
    root = root.resolve()
    run_directory = root / "runs" / run_id
    disposition_path = run_directory / "feature-dispositions.json"
    if disposition_path.exists():
        raise FeatureDispositionError(
            f"feature dispositions already exist and are immutable: {disposition_path}"
        )

    paths = {
        "decision": run_directory / "decision.json",
        "manifest": run_directory / "manifest.json",
        "validation": run_directory / "validation.json",
        "out_of_sample": run_directory / "out-of-sample.json",
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise FeatureDispositionError(
            "required completed evidence is missing: " + ", ".join(missing)
        )

    decision_hash_before = _sha256(paths["decision"])
    manifest = _read_mapping(paths["manifest"])
    feature_set_id = _feature_set_id(manifest)
    feature_set_path = root / "research" / "features" / f"{feature_set_id}.yaml"
    try:
        feature_set = load_feature_set(feature_set_path)
    except (OSError, ValueError) as exc:
        raise FeatureDispositionError(f"invalid feature set: {feature_set_path}: {exc}") from exc
    if feature_set.identifier != feature_set_id:
        raise FeatureDispositionError("feature-set id does not match its manifest reference")

    policy_path = root / "research" / "policies" / f"{feature_set.disposition_policy}.yaml"
    try:
        policy = load_feature_disposition_policy(policy_path)
    except (OSError, ValueError) as exc:
        raise FeatureDispositionError(
            f"invalid feature disposition policy: {policy_path}: {exc}"
        ) from exc
    if len(feature_set.groups) > policy.maximum_feature_groups:
        raise FeatureDispositionError(
            "feature-group count exceeds the committed bounded-analysis policy"
        )

    validation = _read_mapping(paths["validation"])
    oos = _read_mapping(paths["out_of_sample"])
    dispositions = [_dispose_group(group, policy, validation, oos) for group in feature_set.groups]
    payload: dict[str, object] = {
        "artifact_type": "automo.feature_disposition",
        "schema_version": 1,
        "run_id": run_id,
        "experiment_id": manifest.get("experiment_id"),
        "created_at": datetime.now(UTC).isoformat(),
        "feature_set": {
            "id": feature_set.identifier,
            "path": str(feature_set_path.relative_to(root)),
            "sha256": _sha256(feature_set_path),
        },
        "policy": {
            "id": policy.identifier,
            "path": str(policy_path.relative_to(root)),
            "sha256": _sha256(policy_path),
            "contract": asdict(policy),
        },
        "analysis": {
            "kind": "bounded-no-feature-ablation",
            "evaluated_feature_groups": len(feature_set.groups),
            "maximum_feature_groups": policy.maximum_feature_groups,
            "arbitrary_subset_search": False,
            "refit_performed": False,
            "oos_tuning_performed": False,
        },
        "evidence": {
            name: {"path": path.name, "sha256": _sha256(path)} for name, path in paths.items()
        },
        "dispositions": dispositions,
    }
    disposition_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if _sha256(paths["decision"]) != decision_hash_before:
        disposition_path.unlink(missing_ok=True)
        raise FeatureDispositionError("feature analysis changed the immutable experiment decision")
    outcomes = tuple(
        (str(item["feature_group_id"]), FeatureDispositionOutcome(str(item["outcome"])))
        for item in dispositions
    )
    return FeatureDispositionResult(run_id, disposition_path, outcomes)


def _dispose_group(
    group: FeatureGroup,
    policy: FeatureDispositionPolicy,
    validation: dict[str, Any],
    oos: dict[str, Any],
) -> dict[str, object]:
    required = ("observations", "baseline_mse", "candidate_mse")
    missing = [f"validation.{key}" for key in required if key not in validation]
    missing.extend(f"out_of_sample.{key}" for key in required if key not in oos)
    if missing:
        raise FeatureDispositionError("feature evidence fields are missing: " + ", ".join(missing))
    try:
        val_n = int(validation["observations"])
        oos_n = int(oos["observations"])
        val_baseline = float(validation["baseline_mse"])
        val_candidate = float(validation["candidate_mse"])
        oos_baseline = float(oos["baseline_mse"])
        oos_candidate = float(oos["candidate_mse"])
    except (TypeError, ValueError) as exc:
        raise FeatureDispositionError("feature evidence contains non-numeric values") from exc
    values = (val_baseline, val_candidate, oos_baseline, oos_candidate)
    if any(not _finite(value) for value in values):
        raise FeatureDispositionError("feature evidence contains non-finite values")

    if policy.lower_is_better:
        val_effect = val_baseline - val_candidate
        oos_effect = oos_baseline - oos_candidate
    else:
        val_effect = val_candidate - val_baseline
        oos_effect = oos_candidate - oos_baseline

    reasons: list[str]
    if (
        val_n < policy.minimum_validation_observations
        or oos_n < policy.minimum_out_of_sample_observations
    ):
        outcome = FeatureDispositionOutcome.INCONCLUSIVE
        reasons = ["insufficient observations for the committed feature policy"]
    elif (
        val_effect >= policy.minimum_validation_improvement
        and oos_effect >= policy.minimum_out_of_sample_improvement
    ):
        outcome = FeatureDispositionOutcome.RETAINED
        reasons = ["feature group improved validation and out-of-sample evidence"]
    elif (
        val_effect <= -policy.minimum_validation_harm
        and oos_effect <= -policy.minimum_out_of_sample_harm
    ):
        outcome = FeatureDispositionOutcome.REJECTED
        reasons = ["feature group harmed validation and out-of-sample evidence"]
    else:
        outcome = FeatureDispositionOutcome.INCONCLUSIVE
        reasons = ["feature effects were mixed or below committed thresholds"]

    return {
        "feature_group_id": group.identifier,
        "features": list(group.features),
        "description": group.description,
        "ablation_reference": group.ablation_reference,
        "outcome": outcome.value,
        "reasons": reasons,
        "diagnostics": {
            "validation_observations": val_n,
            "out_of_sample_observations": oos_n,
            "validation_effect": val_effect,
            "out_of_sample_effect": oos_effect,
        },
    }


def _feature_set_id(manifest: dict[str, Any]) -> str:
    model = manifest.get("model")
    if isinstance(model, dict):
        value = model.get("feature_set")
        if isinstance(value, str) and value:
            return value
    raise FeatureDispositionError("manifest does not reference a feature set")


def _read_mapping(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FeatureDispositionError(f"invalid JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise FeatureDispositionError(f"evidence must be a mapping: {path}")
    return value


def _finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
