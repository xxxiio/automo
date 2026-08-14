from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from automo.persistence import read_json_artifact, write_json_artifact

from .contracts import ModelPoolSnapshot, ModelPoolSpec, RefreshScoreCard


class PoolStoreError(RuntimeError):
    pass


class FilesystemPoolStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.specs = root / "specs"
        self.snapshots = root / "snapshots"
        self.specs.mkdir(parents=True, exist_ok=True)
        self.snapshots.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, snapshot: ModelPoolSnapshot) -> Path:
        path = self.snapshots / snapshot.pool_id / f"{snapshot.iteration_id}.json"
        if path.exists():
            raise PoolStoreError(f"pool snapshot already exists: {snapshot.pool_id}/{snapshot.iteration_id}")
        payload = asdict(snapshot)
        write_json_artifact(path, artifact_type="automo.model_pool_snapshot", payload=payload)
        return path

    def load_snapshot(self, pool_id: str, iteration_id: str) -> ModelPoolSnapshot:
        raw = read_json_artifact(self.snapshots / pool_id / f"{iteration_id}.json", artifact_type="automo.model_pool_snapshot")
        raw.pop("artifact_type", None)
        raw.pop("schema_version", None)
        raw["scorecards"] = tuple(RefreshScoreCard(**item) for item in raw.get("scorecards", []))
        for key in ("active_model_ids", "selected_model_ids"):
            raw[key] = tuple(raw[key])
        return ModelPoolSnapshot(**raw)

    def history(self, pool_id: str) -> tuple[ModelPoolSnapshot, ...]:
        root = self.snapshots / pool_id
        if not root.is_dir():
            return ()
        return tuple(self.load_snapshot(pool_id, p.stem) for p in sorted(root.glob("*.json")))
