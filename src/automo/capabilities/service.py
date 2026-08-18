"""Governed capability request lifecycle."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from automo.capabilities.contracts import (
    CapabilityRequest,
    CapabilityResultStatus,
    load_capability_request,
)
from automo.contracts import ContractError
from automo.integrations.base import IntegrationStatus


class CapabilityLifecycleError(RuntimeError):
    """Raised when a capability attempt violates its committed contract."""


@dataclass(frozen=True)
class WorkflowFulfillment:
    status: CapabilityResultStatus
    changed_files: tuple[str, ...]
    evidence: tuple[str, ...]
    detail: str


class CapabilityDelegate(Protocol):
    def status(self) -> IntegrationStatus: ...
    def fulfill(self, root: Path, request: CapabilityRequest) -> WorkflowFulfillment: ...


@dataclass(frozen=True)
class CapabilityAttemptResult:
    request_id: str
    attempt_id: str
    status: CapabilityResultStatus
    result_path: Path
    detail: str


def capability_request_path(root: Path, request_id: str) -> Path:
    governed = root / ".automo" / "capabilities" / "requests" / f"{request_id}.yaml"
    legacy = root / "research" / "capabilities" / "requests" / f"{request_id}.yaml"
    return governed if governed.is_file() or not legacy.is_file() else legacy


def inspect_capability(
    root: Path, request_id: str, delegate: CapabilityDelegate
) -> dict[str, object]:
    request = _load_request(root, request_id)
    status = delegate.status()
    attempts = _persisted_attempts(root, request.identifier)
    return {
        "request_id": request.identifier,
        "capability_id": request.capability_id,
        "provider": status.provider,
        "installed": status.installed,
        "enabled": status.enabled,
        "compatible": status.compatible,
        "ready_for_delegation": bool(status.installed and status.enabled and status.compatible),
        "detail": status.detail,
        "persisted_attempts": attempts,
        "latest_attempt_status": attempts[-1]["status"] if attempts else None,
    }


def fulfill_capability(
    root: Path,
    request_id: str,
    *,
    attempt_id: str,
    delegate: CapabilityDelegate,
) -> CapabilityAttemptResult:
    request = _load_request(root, request_id)
    result_dir = root / ".automo" / "capabilities" / "results" / request.identifier / attempt_id
    if result_dir.exists():
        raise CapabilityLifecycleError(f"capability attempt already exists: {result_dir}")

    protected_before = _protected_hashes(root)
    workspace_before = _workspace_snapshot(root)
    provider_status = delegate.status()
    if not (provider_status.installed and provider_status.enabled and provider_status.compatible):
        fulfillment = WorkflowFulfillment(
            status=CapabilityResultStatus.BLOCKED,
            changed_files=(),
            evidence=(),
            detail=provider_status.detail,
        )
    else:
        fulfillment = delegate.fulfill(root, request)

    try:
        actual_changes = _actual_changes(root, workspace_before)
        protected_after = _protected_hashes(root)
        if protected_before != protected_after:
            raise CapabilityLifecycleError(
                "capability workflow altered protected research evidence"
            )
        if set(actual_changes) != set(fulfillment.changed_files):
            raise CapabilityLifecycleError(
                "capability workflow changed files that do not match its declared changed_files"
            )
        _validate_changed_files(request, actual_changes)
        if fulfillment.status == CapabilityResultStatus.FULFILLED and not fulfillment.evidence:
            raise CapabilityLifecycleError(
                "fulfilled capability result must provide validation evidence"
            )
    except Exception:
        _restore_workspace(root, workspace_before)
        raise

    result_dir.mkdir(parents=True)
    result_path = result_dir / "result.json"
    payload = {
        "artifact_type": "automo.capability_result",
        "schema_version": 1,
        "request_id": request.identifier,
        "research_provenance": request.provenance.as_dict() if request.provenance else None,
        "request_hash": _sha256(capability_request_path(root, request.identifier)),
        "attempt_id": attempt_id,
        "provider": provider_status.provider,
        "status": fulfillment.status,
        "detail": fulfillment.detail,
        "changed_files": list(actual_changes),
        "evidence": list(fulfillment.evidence),
        "independent_validation": {
            "declared_changes_match_workspace": True,
            "all_changes_within_scope": True,
            "protected_evidence_unchanged": True,
            "evidence_supplied": bool(fulfillment.evidence)
            if fulfillment.status == CapabilityResultStatus.FULFILLED
            else None,
            "passed": (
                bool(fulfillment.evidence)
                if fulfillment.status == CapabilityResultStatus.FULFILLED
                else True
            ),
        },
        "scope": {
            "allowed_paths": list(request.scope.allowed_paths),
            "forbidden_paths": list(request.scope.forbidden_paths),
        },
        "protected_evidence_hashes_before": protected_before,
        "protected_evidence_hashes_after": protected_after,
        "research_decisions_altered": False,
        "prior_evidence_rewritten": False,
    }
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return CapabilityAttemptResult(
        request_id=request.identifier,
        attempt_id=attempt_id,
        status=fulfillment.status,
        result_path=result_path,
        detail=fulfillment.detail,
    )


def create_getdone_handoff(root: Path, request_id: str) -> Path:
    """Persist a read-only handoff brief for a GetDone-managed development iteration."""
    request = _load_request(root, request_id)
    handoff_dir = root / ".automo" / "capabilities" / "handoffs"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    path = handoff_dir / f"{request.identifier}-getdone.md"
    if path.exists():
        return path
    lines = [
        f"# GetDone capability handoff — {request.identifier}",
        "",
        "Automo remains authoritative for `.automo/` research state. GetDone may use `.agent/` for development state but must not rewrite Automo research evidence or decisions.",
        "",
        "## Requested capability",
        f"- Capability: `{request.capability_id}`",
        f"- Kind: `{request.kind}`",
        f"- Requested by experiment: `{request.experiment}`",
        *(
            [
                f"- Research program: `{request.provenance.program_id}`",
                f"- Hypothesis: `{request.provenance.hypothesis_id}`",
            ]
            if request.provenance
            else []
        ),
        f"- Reason: {request.reason}",
        "",
        "## Requirements",
        *[f"- {item}" for item in request.requirements],
        "",
        "## Acceptance",
        *[f"- {item}" for item in request.acceptance],
        "",
        "## Change boundary",
        "Allowed paths:",
        *[f"- `{item}`" for item in request.scope.allowed_paths],
        "",
        "Forbidden paths:",
        *[f"- `{item}`" for item in request.scope.forbidden_paths],
        "- `.automo/` research state and evidence",
        "",
        "## GetDone usage",
        "Use the current GetDone `guidance` command to load the minimum development guidance for the implementation task, then manage implementation state under `.agent/`. After implementation, return concrete changed-file and test evidence to Automo for independent capability validation.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _load_request(root: Path, request_id: str) -> CapabilityRequest:
    try:
        request = load_capability_request(capability_request_path(root, request_id))
    except ContractError as exc:
        raise CapabilityLifecycleError(str(exc)) from exc
    if request.identifier != request_id:
        raise CapabilityLifecycleError(
            f"capability request id {request.identifier!r} does not match {request_id!r}"
        )
    return request


def _validate_changed_files(request: CapabilityRequest, changed_files: tuple[str, ...]) -> None:
    for raw in changed_files:
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts:
            raise CapabilityLifecycleError(f"unsafe changed path: {raw}")
        normalized = path.as_posix()
        if any(_within(normalized, forbidden) for forbidden in request.scope.forbidden_paths):
            raise CapabilityLifecycleError(f"changed path is forbidden by capability scope: {raw}")
        if not any(_within(normalized, allowed) for allowed in request.scope.allowed_paths):
            raise CapabilityLifecycleError(f"changed path is outside capability scope: {raw}")


def _within(path: str, root: str) -> bool:
    normalized_root = Path(root).as_posix().rstrip("/")
    return path == normalized_root or path.startswith(normalized_root + "/")


def _protected_hashes(root: Path) -> dict[str, str]:
    protected_roots = (
        root / "runs",
        root / "recommendations",
        root / "research" / "experiments",
        root / "research" / "objectives",
        root / "research" / "policies",
        root / ".automo",
    )
    hashes: dict[str, str] = {}
    for protected_root in protected_roots:
        if not protected_root.exists():
            continue
        for path in sorted(item for item in protected_root.rglob("*") if item.is_file()):
            relative = path.relative_to(root).as_posix()
            hashes[relative] = _sha256(path)
    return hashes


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _workspace_snapshot(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    excluded = {".git", ".pytest_cache", "__pycache__", ".agent"}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative_path = path.relative_to(root)
        if any(part in excluded for part in relative_path.parts):
            continue
        snapshot[relative_path.as_posix()] = path.read_bytes()
    return snapshot


def _actual_changes(root: Path, before: dict[str, bytes]) -> tuple[str, ...]:
    after = _workspace_snapshot(root)
    paths = set(before) | set(after)
    return tuple(sorted(path for path in paths if before.get(path) != after.get(path)))


def _restore_workspace(root: Path, before: dict[str, bytes]) -> None:
    after = _workspace_snapshot(root)
    for relative in set(after) - set(before):
        (root / relative).unlink(missing_ok=True)
    for relative, content in before.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _persisted_attempts(root: Path, request_id: str) -> list[dict[str, str]]:
    request_root = root / ".automo" / "capabilities" / "results" / request_id
    attempts: list[dict[str, str]] = []
    if not request_root.exists():
        return attempts
    for result_path in sorted(request_root.glob("*/result.json")):
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        attempts.append(
            {
                "attempt_id": str(payload.get("attempt_id", result_path.parent.name)),
                "status": str(payload.get("status", "unknown")),
                "result_path": result_path.relative_to(root).as_posix(),
            }
        )
    return attempts
