"""Immutable capability request and result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from automo.contracts import ContractError, load_yaml
from automo.governance import ResearchProvenance


class CapabilityResultStatus(StrEnum):
    FULFILLED = "fulfilled"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True)
class CapabilityScope:
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> CapabilityScope:
        allowed = _string_list(value.get("allowed_paths", []), "scope.allowed_paths")
        forbidden = _string_list(value.get("forbidden_paths", []), "scope.forbidden_paths")
        if not allowed:
            raise ContractError("capability scope must contain at least one allowed path")
        return cls(tuple(allowed), tuple(forbidden))


@dataclass(frozen=True)
class CapabilityRequest:
    identifier: str
    experiment: str
    provenance: ResearchProvenance | None
    capability_id: str
    kind: str
    reason: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    requirements: tuple[str, ...]
    acceptance: tuple[str, ...]
    non_goals: tuple[str, ...]
    scope: CapabilityScope

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> CapabilityRequest:
        required = (
            "id",
            "experiment",
            "capability",
            "reason",
            "contract",
            "requirements",
            "acceptance",
            "scope",
        )
        missing = [key for key in required if key not in value]
        if missing:
            raise ContractError(f"capability request missing required keys: {', '.join(missing)}")
        capability = _mapping(value["capability"], "capability")
        contract = _mapping(value["contract"], "contract")
        scope = _mapping(value["scope"], "scope")
        for key in ("id", "kind"):
            if key not in capability:
                raise ContractError(f"capability missing required key: {key}")
        requested_by = value.get("requested_by")
        provenance = None
        if requested_by is not None:
            requested_by = _mapping(requested_by, "requested_by")
            if requested_by.get("program") and requested_by.get("hypothesis"):
                provenance = ResearchProvenance(
                    program_id=_string(requested_by["program"], "requested_by.program"),
                    hypothesis_id=_string(requested_by["hypothesis"], "requested_by.hypothesis"),
                    experiment_id=_optional_string(
                        requested_by.get("experiment"), "requested_by.experiment"
                    ),
                )
        return cls(
            identifier=_string(value["id"], "id"),
            experiment=_string(value["experiment"], "experiment"),
            provenance=provenance,
            capability_id=_string(capability["id"], "capability.id"),
            kind=_string(capability["kind"], "capability.kind"),
            reason=_string(value["reason"], "reason"),
            inputs=tuple(_string_list(contract.get("inputs", []), "contract.inputs")),
            outputs=tuple(_string_list(contract.get("outputs", []), "contract.outputs")),
            requirements=tuple(_string_list(value["requirements"], "requirements")),
            acceptance=tuple(_string_list(value["acceptance"], "acceptance")),
            non_goals=tuple(_string_list(value.get("non_goals", []), "non_goals")),
            scope=CapabilityScope.from_mapping(scope),
        )


def load_capability_request(path: Path) -> CapabilityRequest:
    return CapabilityRequest.from_mapping(load_yaml(path))


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ContractError(f"{field} must be a string-keyed mapping")
    return value


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ContractError(f"{field} must be a list")
    return [_string(item, field) for item in value]


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _string(value, field)
