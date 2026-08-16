from __future__ import annotations

import hashlib
from dataclasses import dataclass

from automo.runtime.contracts import DataSnapshot

from .contracts import DataPartition, EvaluationPartitions


def _ratios(fit: float, validation: float, test: float) -> None:
    if min(fit, validation, test) <= 0 or abs((fit + validation + test) - 1.0) > 1e-9:
        raise ValueError("split fractions must be positive and sum to 1")


def _slice_indices(indices: list[int], fit: float, validation: float) -> EvaluationPartitions:
    n = len(indices)
    a = max(1, int(n * fit))
    b = max(a + 1, int(n * (fit + validation)))
    if b >= n:
        b = n - 1
    return EvaluationPartitions(
        fit=DataPartition("fit", tuple(indices[:a])),
        validation=DataPartition("validation", tuple(indices[a:b])),
        test=DataPartition("test", tuple(indices[b:])),
    )


@dataclass(frozen=True)
class OrderedSplit:
    field: str
    fit_fraction: float = 0.6
    validation_fraction: float = 0.2
    test_fraction: float = 0.2
    id: str = "ordered"

    def split(self, snapshot: DataSnapshot) -> EvaluationPartitions:
        _ratios(self.fit_fraction, self.validation_fraction, self.test_fraction)
        indices = sorted(range(len(snapshot.rows)), key=lambda i: snapshot.rows[i][self.field])
        return _slice_indices(indices, self.fit_fraction, self.validation_fraction)


@dataclass(frozen=True)
class TemporalSplit(OrderedSplit):
    id: str = "temporal"


@dataclass(frozen=True)
class HashSplit:
    key: str
    fit_fraction: float = 0.6
    validation_fraction: float = 0.2
    test_fraction: float = 0.2
    seed: int = 0
    id: str = "hash"

    def split(self, snapshot: DataSnapshot) -> EvaluationPartitions:
        _ratios(self.fit_fraction, self.validation_fraction, self.test_fraction)
        buckets = {"fit": [], "validation": [], "test": []}
        fit_cut = self.fit_fraction
        val_cut = fit_cut + self.validation_fraction
        for i, row in enumerate(snapshot.rows):
            raw = f"{self.seed}:{row[self.key]}".encode()
            value = int(hashlib.sha256(raw).hexdigest()[:16], 16) / float(0xFFFFFFFFFFFFFFFF)
            bucket = "fit" if value < fit_cut else "validation" if value < val_cut else "test"
            buckets[bucket].append(i)
        if not all(buckets.values()):
            raise ValueError(
                "hash split produced an empty partition; provide more rows or a predefined split"
            )
        return EvaluationPartitions(
            *(DataPartition(name, tuple(buckets[name])) for name in ("fit", "validation", "test"))
        )


@dataclass(frozen=True)
class GroupSplit(HashSplit):
    id: str = "group"


@dataclass(frozen=True)
class PredefinedSplit:
    fit_indices: tuple[int, ...]
    validation_indices: tuple[int, ...]
    test_indices: tuple[int, ...]
    id: str = "predefined"

    def split(self, snapshot: DataSnapshot) -> EvaluationPartitions:
        n = len(snapshot.rows)
        all_indices = self.fit_indices + self.validation_indices + self.test_indices
        if not all_indices or min(all_indices) < 0 or max(all_indices) >= n:
            raise ValueError("predefined split contains invalid row indices")
        return EvaluationPartitions(
            DataPartition("fit", self.fit_indices),
            DataPartition("validation", self.validation_indices),
            DataPartition("test", self.test_indices),
        )
