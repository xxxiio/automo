"""Optional workflow-provider boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from automo.capabilities.contracts import CapabilityRequest
    from automo.capabilities.service import WorkflowFulfillment


@dataclass(frozen=True)
class IntegrationStatus:
    provider: str
    installed: bool
    enabled: bool
    compatible: bool
    detail: str


class CapabilityWorkflow(Protocol):
    def status(self) -> IntegrationStatus:
        ...

    def fulfill(self, root: Path, request: "CapabilityRequest") -> "WorkflowFulfillment":
        ...
