from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

import yaml


class ArtifactError(RuntimeError):
    """Raised when a persisted Automo artifact cannot be decoded safely."""


def _envelope(artifact_type: str, payload: Mapping[str, Any], schema_version: int) -> dict[str, Any]:
    if schema_version < 1:
        raise ValueError("schema_version must be positive")
    return {
        "artifact_type": artifact_type,
        "schema_version": schema_version,
        **dict(payload),
    }


def _validate(raw: Any, *, artifact_type: str | None, path: Path) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ArtifactError(f"invalid Automo artifact: {path}")
    stored_type = raw.get("artifact_type")
    stored_version = raw.get("schema_version")
    if stored_type is None or stored_version is None:
        raise ArtifactError(f"artifact is missing artifact_type/schema_version: {path}")
    if artifact_type is not None and stored_type != artifact_type:
        raise ArtifactError(
            f"unexpected artifact type in {path}: expected {artifact_type!r}, got {stored_type!r}"
        )
    if not isinstance(stored_version, int) or stored_version < 1:
        raise ArtifactError(f"invalid schema_version in {path}: {stored_version!r}")
    return raw


def write_json_artifact(
    path: Path,
    *,
    artifact_type: str,
    payload: Mapping[str, Any],
    schema_version: int = 1,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = _envelope(artifact_type, payload, schema_version)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(document, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
        temp = Path(handle.name)
    os.replace(temp, path)


def read_json_artifact(path: Path, *, artifact_type: str | None = None) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"could not read Automo artifact {path}: {exc}") from exc
    return _validate(raw, artifact_type=artifact_type, path=path)


def write_yaml_artifact(
    path: Path,
    *,
    artifact_type: str,
    payload: Mapping[str, Any],
    schema_version: int = 1,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = _envelope(artifact_type, payload, schema_version)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        yaml.safe_dump(document, handle, sort_keys=False, allow_unicode=True)
        temp = Path(handle.name)
    os.replace(temp, path)


def read_yaml_artifact(path: Path, *, artifact_type: str | None = None) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ArtifactError(f"could not read Automo artifact {path}: {exc}") from exc
    return _validate(raw, artifact_type=artifact_type, path=path)
