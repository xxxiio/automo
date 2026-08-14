from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class InterventionKind(StrEnum):
    MODEL = "model"
    PARAMETERS = "parameters"
    FEATURE_SET = "feature_set"
    FEATURE_ADDITION = "feature_addition"
    FEATURE_REMOVAL = "feature_removal"
    CALIBRATION = "calibration"
    TRAINING_WINDOW = "training_window"
    NODE_MODEL = "node_model"
    MODEL_INPUT_ADDITION = "model_input_addition"
    MODEL_INPUT_REMOVAL = "model_input_removal"


@dataclass(frozen=True)
class ResearchIntervention:
    kind: InterventionKind
    values: Mapping[str, Any]

    def fingerprint_payload(self) -> Mapping[str, Any]:
        return {"kind": self.kind.value, "values": dict(sorted(self.values.items()))}


@dataclass(frozen=True)
class ResearchSearchSpace:
    id: str
    model_spec_ids: tuple[str, ...] = ()
    feature_set_ids: tuple[str, ...] = ()
    calibrator_ids: tuple[str, ...] = ()
    parameter_choices: Mapping[str, tuple[Any, ...]] = field(default_factory=dict)
    maximum_compound_interventions: int = 1


@dataclass(frozen=True)
class ResearchBudget:
    maximum_candidates: int = 8
    maximum_model_fits: int = 24
    maximum_oos_candidates: int = 2
    maximum_runtime_minutes: float = 120
    maximum_compute_cost: float = 0

    def __post_init__(self) -> None:
        if min(self.maximum_candidates, self.maximum_model_fits, self.maximum_oos_candidates) < 1:
            raise ValueError("research budget counts must be positive")
        if self.maximum_oos_candidates > self.maximum_candidates:
            raise ValueError("OOS candidate budget cannot exceed candidate budget")


@dataclass(frozen=True)
class ResearchSafeguards:
    minimum_improvement: float = 0.0
    minimum_improving_fold_fraction: float = 0.5
    minimum_validation_observations: int = 1
    minimum_oos_observations: int = 1


@dataclass(frozen=True)
class CandidateProposal:
    id: str
    baseline_model_spec_id: str
    intervention: ResearchIntervention
    rationale: tuple[str, ...]
    expected_effect: str
    falsification: tuple[str, ...]
    priority: int

    @property
    def fingerprint(self) -> str:
        payload = {
            "baseline": self.baseline_model_spec_id,
            "intervention": self.intervention.fingerprint_payload(),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class ResearchPlan:
    id: str
    baseline_model_spec_id: str
    data_source_id: str
    split_strategy_id: str
    diagnosis: str
    findings: tuple[str, ...]
    search_space: ResearchSearchSpace
    budget: ResearchBudget
    safeguards: ResearchSafeguards
    candidates: tuple[CandidateProposal, ...]


class CandidateStage(StrEnum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    SHORTLISTED = "shortlisted"
    OOS_EVALUATED = "oos_evaluated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class CandidateResult:
    candidate_id: str
    fingerprint: str
    stage: CandidateStage
    validation_metric: float | None = None
    oos_metric: float | None = None
    baseline_validation_metric: float | None = None
    baseline_oos_metric: float | None = None
    validation_count: int = 0
    oos_count: int = 0
    registered_model_id: str | None = None
    calibration_id: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class ResearchIterationReport:
    id: str
    plan_id: str
    proposals_count: int
    validation_trials: int
    oos_trials: int
    repeated_validation_exposure: int
    results: tuple[CandidateResult, ...]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for row in payload["results"]:
            row["stage"] = row["stage"].value if hasattr(row["stage"], "value") else row["stage"]
        return payload
