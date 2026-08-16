"""Core immutable contracts for research objectives and experiments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class ContractError(ValueError):
    """Raised when a persisted research contract is incomplete or inconsistent."""


class ExperimentStatus(StrEnum):
    PROPOSED = "proposed"
    READY = "ready"
    VALIDATING = "validating"
    BLOCKED = "blocked"
    WAITING_FOR_CAPABILITY = "waiting-for-capability"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    DIAGNOSING = "diagnosing"
    COMPLETED = "completed"
    INVALID = "invalid"


class FeatureDispositionOutcome(StrEnum):
    RETAINED = "retained"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class DecisionOutcome(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"
    INVALID = "invalid"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ResearchObjective:
    identifier: str
    status: str
    outcome: str
    primary_metric: str
    secondary_metrics: tuple[str, ...]
    current_champion: str | None
    next_experiment: str

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> ResearchObjective:
        required = ("id", "status", "outcome", "primary_metric", "next_experiment")
        _require_keys(value, required, "research objective")
        return cls(
            identifier=_string(value["id"], "id"),
            status=_string(value["status"], "status"),
            outcome=_string(value["outcome"], "outcome"),
            primary_metric=_string(value["primary_metric"], "primary_metric"),
            secondary_metrics=tuple(_string_list(value.get("secondary_metrics", []))),
            current_champion=_optional_string(value.get("current_champion"), "current_champion"),
            next_experiment=_string(value["next_experiment"], "next_experiment"),
        )


@dataclass(frozen=True)
class DataRequirement:
    identifier: str
    required_fields: tuple[str, ...]
    minimum_start: str | None
    minimum_end: str | None

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> DataRequirement:
        _require_keys(value, ("id",), "data requirement")
        return cls(
            identifier=_string(value["id"], "data requirement id"),
            required_fields=tuple(_string_list(value.get("required_fields", []))),
            minimum_start=_optional_string(value.get("minimum_start"), "minimum_start"),
            minimum_end=_optional_string(value.get("minimum_end"), "minimum_end"),
        )


@dataclass(frozen=True)
class CapabilityRequirement:
    identifier: str
    kind: str

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> CapabilityRequirement:
        _require_keys(value, ("id", "kind"), "capability requirement")
        return cls(
            identifier=_string(value["id"], "capability id"),
            kind=_string(value["kind"], "capability kind"),
        )


@dataclass(frozen=True)
class ExperimentSpec:
    identifier: str
    objective: str
    status: ExperimentStatus
    title: str
    why_next: str
    hypothesis: str
    rationale: tuple[str, ...]
    expected_effect: str
    falsification: tuple[str, ...]
    baseline: str
    candidate_model: str
    feature_set: str
    data_requirements: tuple[DataRequirement, ...]
    capability_requirements: tuple[CapabilityRequirement, ...]
    split_spec: str
    evaluation_spec: str
    decision_policy: str
    maximum_trials: int
    maximum_runtime_minutes: int
    maximum_compute_cost: float

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> ExperimentSpec:
        required = (
            "id",
            "objective",
            "status",
            "title",
            "why_next",
            "hypothesis",
            "baseline",
            "candidate",
            "data",
            "split_spec",
            "evaluation_spec",
            "decision_policy",
            "budget",
            "falsification",
        )
        _require_keys(value, required, "experiment")
        candidate = _mapping(value["candidate"], "candidate")
        budget = _mapping(value["budget"], "budget")
        _require_keys(candidate, ("model", "feature_set"), "candidate")
        _require_keys(
            budget,
            ("maximum_trials", "maximum_runtime_minutes", "maximum_compute_cost"),
            "budget",
        )
        try:
            status = ExperimentStatus(_string(value["status"], "status"))
        except ValueError as exc:
            raise ContractError(f"unknown experiment status: {value['status']!r}") from exc
        return cls(
            identifier=_string(value["id"], "id"),
            objective=_string(value["objective"], "objective"),
            status=status,
            title=_string(value["title"], "title"),
            why_next=_string(value["why_next"], "why_next"),
            hypothesis=_string(value["hypothesis"], "hypothesis"),
            rationale=tuple(_string_list(value.get("rationale", []))),
            expected_effect=_string(
                value.get("expected_effect", "not specified"), "expected_effect"
            ),
            falsification=tuple(_string_list(value["falsification"])),
            baseline=_string(value["baseline"], "baseline"),
            candidate_model=_string(candidate["model"], "candidate.model"),
            feature_set=_string(candidate["feature_set"], "candidate.feature_set"),
            data_requirements=tuple(
                DataRequirement.from_mapping(_mapping(item, "data item"))
                for item in _list(value["data"], "data")
            ),
            capability_requirements=tuple(
                CapabilityRequirement.from_mapping(_mapping(item, "capability item"))
                for item in _list(value.get("capabilities", []), "capabilities")
            ),
            split_spec=_string(value["split_spec"], "split_spec"),
            evaluation_spec=_string(value["evaluation_spec"], "evaluation_spec"),
            decision_policy=_string(value["decision_policy"], "decision_policy"),
            maximum_trials=_positive_int(budget["maximum_trials"], "maximum_trials"),
            maximum_runtime_minutes=_positive_int(
                budget["maximum_runtime_minutes"], "maximum_runtime_minutes"
            ),
            maximum_compute_cost=_non_negative_float(
                budget["maximum_compute_cost"], "maximum_compute_cost"
            ),
        )


@dataclass(frozen=True)
class FeatureGroup:
    identifier: str
    features: tuple[str, ...]
    description: str
    ablation_reference: str

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> FeatureGroup:
        _require_keys(
            value, ("id", "features", "description", "ablation_reference"), "feature group"
        )
        features = tuple(_string_list(value["features"]))
        if not features:
            raise ContractError("feature group must contain at least one feature")
        return cls(
            identifier=_string(value["id"], "feature group id"),
            features=features,
            description=_string(value["description"], "feature group description"),
            ablation_reference=_string(value["ablation_reference"], "ablation_reference"),
        )


@dataclass(frozen=True)
class FeatureSetSpec:
    identifier: str
    disposition_policy: str
    groups: tuple[FeatureGroup, ...]

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> FeatureSetSpec:
        _require_keys(value, ("id", "disposition_policy", "groups"), "feature set")
        groups = tuple(
            FeatureGroup.from_mapping(_mapping(item, "feature group"))
            for item in _list(value["groups"], "groups")
        )
        if not groups:
            raise ContractError("feature set must contain at least one feature group")
        identifiers = [group.identifier for group in groups]
        if len(set(identifiers)) != len(identifiers):
            raise ContractError("feature group ids must be unique")
        return cls(
            identifier=_string(value["id"], "id"),
            disposition_policy=_string(value["disposition_policy"], "disposition_policy"),
            groups=groups,
        )


@dataclass(frozen=True)
class FeatureDispositionPolicy:
    identifier: str
    metric: str
    lower_is_better: bool
    minimum_validation_observations: int
    minimum_out_of_sample_observations: int
    minimum_validation_improvement: float
    minimum_out_of_sample_improvement: float
    minimum_validation_harm: float
    minimum_out_of_sample_harm: float
    maximum_feature_groups: int

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> FeatureDispositionPolicy:
        required = (
            "id",
            "metric",
            "lower_is_better",
            "minimum_validation_observations",
            "minimum_out_of_sample_observations",
            "minimum_validation_improvement",
            "minimum_out_of_sample_improvement",
            "minimum_validation_harm",
            "minimum_out_of_sample_harm",
            "maximum_feature_groups",
        )
        _require_keys(value, required, "feature disposition policy")
        if not isinstance(value["lower_is_better"], bool):
            raise ContractError("lower_is_better must be a boolean")
        return cls(
            identifier=_string(value["id"], "id"),
            metric=_string(value["metric"], "metric"),
            lower_is_better=value["lower_is_better"],
            minimum_validation_observations=_positive_int(
                value["minimum_validation_observations"], "minimum_validation_observations"
            ),
            minimum_out_of_sample_observations=_positive_int(
                value["minimum_out_of_sample_observations"], "minimum_out_of_sample_observations"
            ),
            minimum_validation_improvement=_non_negative_float(
                value["minimum_validation_improvement"], "minimum_validation_improvement"
            ),
            minimum_out_of_sample_improvement=_non_negative_float(
                value["minimum_out_of_sample_improvement"], "minimum_out_of_sample_improvement"
            ),
            minimum_validation_harm=_non_negative_float(
                value["minimum_validation_harm"], "minimum_validation_harm"
            ),
            minimum_out_of_sample_harm=_non_negative_float(
                value["minimum_out_of_sample_harm"], "minimum_out_of_sample_harm"
            ),
            maximum_feature_groups=_positive_int(
                value["maximum_feature_groups"], "maximum_feature_groups"
            ),
        )


@dataclass(frozen=True)
class DecisionPolicy:
    identifier: str
    metric: str
    lower_is_better: bool
    minimum_validation_observations: int
    minimum_out_of_sample_observations: int
    minimum_validation_improvement: float
    minimum_out_of_sample_improvement: float
    maximum_oos_degradation_from_validation: float
    require_directional_agreement: bool

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> DecisionPolicy:
        required = (
            "id",
            "metric",
            "lower_is_better",
            "minimum_validation_observations",
            "minimum_out_of_sample_observations",
            "minimum_validation_improvement",
            "minimum_out_of_sample_improvement",
            "maximum_oos_degradation_from_validation",
            "require_directional_agreement",
        )
        _require_keys(value, required, "decision policy")
        lower_is_better = value["lower_is_better"]
        require_directional_agreement = value["require_directional_agreement"]
        if not isinstance(lower_is_better, bool):
            raise ContractError("lower_is_better must be a boolean")
        if not isinstance(require_directional_agreement, bool):
            raise ContractError("require_directional_agreement must be a boolean")
        return cls(
            identifier=_string(value["id"], "id"),
            metric=_string(value["metric"], "metric"),
            lower_is_better=lower_is_better,
            minimum_validation_observations=_positive_int(
                value["minimum_validation_observations"], "minimum_validation_observations"
            ),
            minimum_out_of_sample_observations=_positive_int(
                value["minimum_out_of_sample_observations"],
                "minimum_out_of_sample_observations",
            ),
            minimum_validation_improvement=_non_negative_float(
                value["minimum_validation_improvement"], "minimum_validation_improvement"
            ),
            minimum_out_of_sample_improvement=_non_negative_float(
                value["minimum_out_of_sample_improvement"],
                "minimum_out_of_sample_improvement",
            ),
            maximum_oos_degradation_from_validation=_non_negative_float(
                value["maximum_oos_degradation_from_validation"],
                "maximum_oos_degradation_from_validation",
            ),
            require_directional_agreement=require_directional_agreement,
        )


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"contract does not exist: {path}") from exc
    except yaml.YAMLError as exc:
        raise ContractError(f"invalid YAML in {path}: {exc}") from exc
    return _mapping(value, str(path))


def load_experiment(path: Path) -> ExperimentSpec:
    return ExperimentSpec.from_mapping(load_yaml(path))


def load_objective(path: Path) -> ResearchObjective:
    return ResearchObjective.from_mapping(load_yaml(path))


def load_decision_policy(path: Path) -> DecisionPolicy:
    return DecisionPolicy.from_mapping(load_yaml(path))


def load_feature_set(path: Path) -> FeatureSetSpec:
    return FeatureSetSpec.from_mapping(load_yaml(path))


def load_feature_disposition_policy(path: Path) -> FeatureDispositionPolicy:
    return FeatureDispositionPolicy.from_mapping(load_yaml(path))


def _require_keys(value: dict[str, Any], keys: tuple[str, ...], context: str) -> None:
    missing = [key for key in keys if key not in value]
    if missing:
        raise ContractError(f"{context} missing required keys: {', '.join(missing)}")


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ContractError(f"{field} must be a string-keyed mapping")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{field} must be a list")
    return value


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _string(value, field)


def _string_list(value: Any) -> list[str]:
    return [_string(item, "list item") for item in _list(value, "string list")]


def _positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ContractError(f"{field} must be a positive integer")
    return value


def _non_negative_float(value: Any, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ContractError(f"{field} must be a non-negative number")
    return float(value)
