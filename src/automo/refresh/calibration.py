from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AffineCalibrationModel:
    slope: float
    intercept: float

    def transform(self, prediction: Sequence[float]) -> tuple[float, ...]:
        return tuple(self.slope * float(x) + self.intercept for x in prediction)


class AffineCalibrationCodec:
    id = "automo-affine-json-v1"

    def save(self, calibration: AffineCalibrationModel, path: Path) -> None:
        path.write_text(
            json.dumps({"slope": calibration.slope, "intercept": calibration.intercept}),
            encoding="utf-8",
        )

    def load(self, path: Path) -> AffineCalibrationModel:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return AffineCalibrationModel(float(raw["slope"]), float(raw["intercept"]))


class AffineCalibrator:
    id = "affine"
    artifact_codec = AffineCalibrationCodec()

    def fit(self, prediction: Sequence[float], target: Sequence[float]) -> AffineCalibrationModel:
        if len(prediction) != len(target) or not prediction:
            raise ValueError("calibration requires equal non-empty prediction and target sequences")
        x = [float(v) for v in prediction]
        y = [float(v) for v in target]
        mx = sum(x) / len(x)
        my = sum(y) / len(y)
        variance = sum((v - mx) ** 2 for v in x)
        slope = (
            0.0
            if variance == 0
            else sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / variance
        )
        return AffineCalibrationModel(slope=slope, intercept=my - slope * mx)
