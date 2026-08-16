"""Deterministic prerequisite checks and user-action blockers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from automo.contracts import CapabilityRequirement, DataRequirement, ExperimentSpec


class BlockerType(StrEnum):
    UNAVAILABLE_DATA_SOURCE = "unavailable-data-source"
    MISSING_DATA_FIELDS = "missing-data-fields"
    INSUFFICIENT_DATA_COVERAGE = "insufficient-data-coverage"
    MISSING_CAPABILITY = "missing-capability"


@dataclass(frozen=True)
class DataAvailability:
    available: bool
    fields: frozenset[str] = frozenset()
    start: str | None = None
    end: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class Blocker:
    type: BlockerType
    requirement_id: str
    reason: str
    user_action_required: str


@dataclass(frozen=True)
class PrerequisiteReport:
    experiment_id: str
    blockers: tuple[Blocker, ...]

    @property
    def ready(self) -> bool:
        return not self.blockers


class DataCatalogue(Protocol):
    def inspect(self, requirement_id: str) -> DataAvailability: ...


class CapabilityCatalogue(Protocol):
    def contains(self, requirement_id: str) -> bool: ...


class MappingDataCatalogue:
    def __init__(self, values: dict[str, DataAvailability]) -> None:
        self._values = dict(values)

    def inspect(self, requirement_id: str) -> DataAvailability:
        return self._values.get(
            requirement_id,
            DataAvailability(False, detail="source is not registered"),
        )


class SetCapabilityCatalogue:
    def __init__(self, identifiers: set[str] | frozenset[str]) -> None:
        self._identifiers = frozenset(identifiers)

    def contains(self, requirement_id: str) -> bool:
        return requirement_id in self._identifiers


def validate_prerequisites(
    experiment: ExperimentSpec,
    data: DataCatalogue,
    capabilities: CapabilityCatalogue,
) -> PrerequisiteReport:
    blockers: list[Blocker] = []
    for requirement in experiment.data_requirements:
        blockers.extend(_data_blockers(requirement, data.inspect(requirement.identifier)))
    for requirement in experiment.capability_requirements:
        blocker = _capability_blocker(requirement, capabilities)
        if blocker is not None:
            blockers.append(blocker)
    return PrerequisiteReport(experiment.identifier, tuple(blockers))


def _data_blockers(
    requirement: DataRequirement,
    availability: DataAvailability,
) -> tuple[Blocker, ...]:
    if not availability.available:
        detail = availability.detail or "source could not be inspected"
        return (
            Blocker(
                BlockerType.UNAVAILABLE_DATA_SOURCE,
                requirement.identifier,
                detail,
                f"Provide or approve access to data source {requirement.identifier}.",
            ),
        )
    blockers: list[Blocker] = []
    missing = sorted(set(requirement.required_fields) - availability.fields)
    if missing:
        blockers.append(
            Blocker(
                BlockerType.MISSING_DATA_FIELDS,
                requirement.identifier,
                f"required fields are unavailable: {', '.join(missing)}",
                f"Provide a point-in-time-safe source containing: {', '.join(missing)}.",
            )
        )
    if requirement.minimum_start and (
        availability.start is None or availability.start > requirement.minimum_start
    ):
        blockers.append(
            Blocker(
                BlockerType.INSUFFICIENT_DATA_COVERAGE,
                requirement.identifier,
                f"data starts at {availability.start!r}; requires {requirement.minimum_start}",
                f"Provide historical coverage from {requirement.minimum_start}.",
            )
        )
    if requirement.minimum_end and (
        availability.end is None or availability.end < requirement.minimum_end
    ):
        blockers.append(
            Blocker(
                BlockerType.INSUFFICIENT_DATA_COVERAGE,
                requirement.identifier,
                f"data ends at {availability.end!r}; requires {requirement.minimum_end}",
                f"Provide coverage through {requirement.minimum_end}.",
            )
        )
    return tuple(blockers)


def _capability_blocker(
    requirement: CapabilityRequirement,
    capabilities: CapabilityCatalogue,
) -> Blocker | None:
    if capabilities.contains(requirement.identifier):
        return None
    return Blocker(
        BlockerType.MISSING_CAPABILITY,
        requirement.identifier,
        f"required {requirement.kind} capability is not registered",
        f"Implement and register capability {requirement.identifier}.",
    )
