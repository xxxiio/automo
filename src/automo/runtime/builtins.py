from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import DataSnapshot, FeatureSpec, ModelSpec


@dataclass(frozen=True)
class CsvDataSource:
    id: str
    path: Path
    as_of_field: str | None = None

    def snapshot(self) -> DataSnapshot:
        with self.path.open(newline="", encoding="utf-8") as handle:
            rows = tuple(dict(row) for row in csv.DictReader(handle))
        content_hash = hashlib.sha256(self.path.read_bytes()).hexdigest()
        return DataSnapshot(
            id=self.id, rows=rows, as_of_field=self.as_of_field, content_hash=content_hash
        )


@dataclass(frozen=True)
class LambdaFeature:
    spec: FeatureSpec
    function: Any

    def compute(self, row: Mapping[str, Any], resolved: Mapping[str, Any]) -> Any:
        return self.function(row, resolved)


@dataclass(frozen=True)
class _LinearModel:
    feature: str
    intercept: float
    slope: float

    def predict(self, rows: Sequence[Mapping[str, Any]]) -> tuple[float, ...]:
        return tuple(self.intercept + self.slope * float(row[self.feature]) for row in rows)


class SingleFeatureLinearRunner:
    implementation = "linear.single_feature"

    @property
    def artifact_codec(self):
        return LinearModelJsonCodec()

    def fit(
        self, spec: ModelSpec, rows: Sequence[Mapping[str, Any]], *, target: Sequence[float]
    ) -> _LinearModel:
        if len(rows) != len(target) or not rows:
            raise ValueError("rows and target must be non-empty and aligned")
        features = tuple(rows[0].keys())
        if len(features) != 1:
            raise ValueError(
                "single-feature linear runner requires exactly one materialized feature"
            )
        feature = features[0]
        x = [float(row[feature]) for row in rows]
        y = [float(value) for value in target]
        xbar = sum(x) / len(x)
        ybar = sum(y) / len(y)
        denom = sum((value - xbar) ** 2 for value in x)
        slope = (
            0.0
            if denom == 0
            else sum((a - xbar) * (b - ybar) for a, b in zip(x, y, strict=True)) / denom
        )
        return _LinearModel(feature, ybar - slope * xbar, slope)


class MeanSquaredError:
    id = "mse"

    def evaluate(self, truth: Sequence[float], prediction: Sequence[float]) -> float:
        if len(truth) != len(prediction) or not truth:
            raise ValueError("truth and prediction must be non-empty and aligned")
        return sum(
            (float(a) - float(b)) ** 2 for a, b in zip(truth, prediction, strict=True)
        ) / len(truth)


class LinearModelJsonCodec:
    id = "builtin.linear-json-v1"

    def save(self, model: _LinearModel, path: Path) -> None:
        payload = {"feature": model.feature, "intercept": model.intercept, "slope": model.slope}
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def load(self, path: Path) -> _LinearModel:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _LinearModel(
            feature=str(payload["feature"]),
            intercept=float(payload["intercept"]),
            slope=float(payload["slope"]),
        )
