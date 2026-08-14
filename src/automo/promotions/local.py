"""Non-deploying champion/challenger promotion recommendations."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class PromotionError(RuntimeError):
    pass


class PromotionOutcome(StrEnum):
    PROMOTE_CHALLENGER = "promote-challenger"
    RETAIN_CHAMPION = "retain-champion"
    INVALID_EVIDENCE = "invalid-evidence"


@dataclass(frozen=True)
class PromotionResult:
    recommendation_path: Path
    outcome: PromotionOutcome
    reasons: tuple[str, ...]


def recommend_promotion(root: Path, *, recommendation_id: str = "promotion-0001") -> PromotionResult:
    root = root.resolve()
    output_dir = root / "recommendations" / recommendation_id
    if output_dir.exists():
        raise PromotionError(f"recommendation directory already exists and is immutable: {output_dir}")
    decision_path = root / "runs/experiment-0003-decision/decision.json"
    temporal_path = root / "runs/experiment-0006-temporal/temporal-stability.json"
    manifest_path = root / "runs/experiment-0003-decision/manifest.json"
    policy_path = root / "research/policies/POLICY-PROMOTION-0001.yaml"
    paths = (decision_path, temporal_path, manifest_path, policy_path)
    if any(not p.is_file() for p in paths):
        missing = [str(p.relative_to(root)) for p in paths if not p.is_file()]
        raise PromotionError(f"required promotion evidence is unavailable: {missing}")

    try:
        decision = _json(decision_path)
        temporal = _json(temporal_path)
        manifest = _json(manifest_path)
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        if not isinstance(policy, dict):
            raise ValueError("policy must be a mapping")
        val_imp = float(decision["diagnostics"]["validation_improvement"])
        oos_imp = float(decision["diagnostics"]["out_of_sample_improvement"])
        folds = int(temporal["trials_executed"])
        improved = int(temporal["aggregate"]["out_of_sample_improved_folds"])
        duration_ms = float(manifest["duration_ms"])
        cost = float(manifest["compute_cost"]) + float(temporal["compute_cost"])
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        raise PromotionError("promotion evidence is malformed") from exc

    failures: list[str] = []
    if decision.get("outcome") != policy["required_decision_outcome"]:
        failures.append("quality decision did not meet the committed outcome")
    if val_imp < float(policy["minimum_validation_improvement"]):
        failures.append("validation improvement missed the committed gate")
    if oos_imp < float(policy["minimum_out_of_sample_improvement"]):
        failures.append("out-of-sample improvement missed the committed gate")
    fraction = improved / folds if folds else 0.0
    if fraction < float(policy["minimum_temporal_improved_fraction"]):
        failures.append("temporal improved-fold fraction missed the committed gate")
    if bool(policy["require_temporal_directional_agreement"]) and not bool(temporal["aggregate"]["directional_agreement"]):
        failures.append("temporal directions disagree")
    if duration_ms > float(policy["maximum_duration_ms"]):
        failures.append("latency exceeded the committed gate")
    if cost > float(policy["maximum_compute_cost"]):
        failures.append("cost exceeded the committed gate")

    outcome = PromotionOutcome.RETAIN_CHAMPION if failures else PromotionOutcome.PROMOTE_CHALLENGER
    reasons = tuple(failures or ["all committed quality, stability, latency, and cost gates passed"])
    output_dir.mkdir(parents=True)
    payload = {
        "artifact_type": "automo.promotion_recommendation",
        "schema_version": 1,
        "recommendation_id": recommendation_id,
        "outcome": outcome,
        "champion": "BASELINE-NAIVE-0001",
        "challenger": "MODEL-LINEAR-0001",
        "reasons": reasons,
        "gates": {
            "validation_improvement": val_imp,
            "out_of_sample_improvement": oos_imp,
            "temporal_improved_fraction": fraction,
            "temporal_directional_agreement": temporal["aggregate"]["directional_agreement"],
            "duration_ms": duration_ms,
            "compute_cost": cost,
        },
        "evidence": {str(p.relative_to(root)): _sha256(p) for p in paths},
        "deployment_performed": False,
        "refit_performed": False,
        "prior_evidence_rewritten": False,
    }
    recommendation_path = output_dir / "recommendation.json"
    recommendation_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return PromotionResult(recommendation_path, outcome, reasons)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("evidence must be a mapping")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
