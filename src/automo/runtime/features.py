from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import FeatureComputer, FeatureSetSpec


class FeatureGraphError(RuntimeError):
    pass


class FeatureEngine:
    def __init__(self, computers: tuple[FeatureComputer, ...]) -> None:
        self._computers = {item.spec.id: item for item in computers}

    def materialize(self, rows: tuple[Mapping[str, Any], ...], feature_set: FeatureSetSpec) -> tuple[dict[str, Any], ...]:
        return tuple(self._materialize_row(row, feature_set) for row in rows)

    def _materialize_row(self, row: Mapping[str, Any], feature_set: FeatureSetSpec) -> dict[str, Any]:
        resolved: dict[str, Any] = dict(row)
        visiting: set[str] = set()

        def resolve(feature_id: str) -> Any:
            if feature_id in resolved:
                return resolved[feature_id]
            if feature_id in visiting:
                raise FeatureGraphError(f"feature dependency cycle at {feature_id}")
            computer = self._computers.get(feature_id)
            if computer is None:
                raise FeatureGraphError(f"unknown feature: {feature_id}")
            if not computer.spec.point_in_time_safe:
                raise FeatureGraphError(f"feature is not declared point-in-time safe: {feature_id}")
            visiting.add(feature_id)
            for dependency in computer.spec.dependencies:
                resolve(dependency)
            value = computer.compute(row, resolved)
            visiting.remove(feature_id)
            resolved[feature_id] = value
            return value

        return {feature_id: resolve(feature_id) for feature_id in feature_set.features}
