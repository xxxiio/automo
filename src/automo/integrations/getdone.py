"""Lazy GetDone integration discovery without a hard dependency."""

from __future__ import annotations

from collections.abc import Callable
from importlib import metadata, util
from pathlib import Path

from automo.capabilities.contracts import CapabilityRequest, CapabilityResultStatus
from automo.capabilities.service import WorkflowFulfillment
from automo.integrations.base import IntegrationStatus

GetDoneDelegate = Callable[[Path, CapabilityRequest], WorkflowFulfillment]


class GetDoneCapabilityWorkflow:
    """Optional explicit adapter for compatible GetDone capability workflows.

    A delegate can be injected by an embedding application. Otherwise the adapter
    looks for exactly one ``automo.capability_workflows`` entry point named
    ``default``. Merely installing GetDone never triggers workflow execution.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        delegate: GetDoneDelegate | None = None,
    ) -> None:
        self._enabled = enabled
        self._delegate = delegate

    def status(self) -> IntegrationStatus:
        installed = util.find_spec("getdone") is not None or self._delegate is not None
        if not installed:
            return IntegrationStatus(
                provider="getdone",
                installed=False,
                enabled=self._enabled,
                compatible=False,
                detail='Install with: pip install "automo[getdone]"',
            )
        compatible = self._delegate is not None or _find_entry_point() is not None
        version = _distribution_version()
        if not compatible:
            detail = (
                f"GetDone {version} is installed, but no compatible capability workflow "
                "entry point is registered."
            )
        else:
            detail = f"GetDone {version} capability delegation is available and remains explicit."
        return IntegrationStatus(
            provider="getdone",
            installed=True,
            enabled=self._enabled,
            compatible=compatible,
            detail=detail,
        )

    def fulfill(self, root: Path, request: CapabilityRequest) -> WorkflowFulfillment:
        status = self.status()
        if not (status.installed and status.enabled and status.compatible):
            return WorkflowFulfillment(
                status=CapabilityResultStatus.BLOCKED,
                changed_files=(),
                evidence=(),
                detail=status.detail,
            )
        delegate = self._delegate
        if delegate is None:
            entry_point = _find_entry_point()
            if entry_point is None:
                return WorkflowFulfillment(
                    status=CapabilityResultStatus.BLOCKED,
                    changed_files=(),
                    evidence=(),
                    detail="No compatible GetDone capability workflow is registered.",
                )
            delegate = entry_point.load()
        result = delegate(root, request)
        if not isinstance(result, WorkflowFulfillment):
            raise TypeError("GetDone capability delegate must return WorkflowFulfillment")
        return result


def _find_entry_point() -> metadata.EntryPoint | None:
    try:
        selected = metadata.entry_points(group="automo.capability_workflows")
    except TypeError:  # pragma: no cover - compatibility with older importlib.metadata
        selected = metadata.entry_points().get("automo.capability_workflows", ())
    matches = [entry for entry in selected if entry.name == "default"]
    return matches[0] if len(matches) == 1 else None


def _distribution_version() -> str:
    for name in ("getdone-dev", "get-done", "getdone"):
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return "injected"
