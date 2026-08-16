import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from automo.capabilities import (
    CapabilityLifecycleError,
    CapabilityResultStatus,
    WorkflowFulfillment,
    fulfill_capability,
    inspect_capability,
    load_capability_request,
)
from automo.cli import app
from automo.integrations.base import IntegrationStatus


class FakeWorkflow:
    def __init__(self, *, changed_files: tuple[str, ...] = ()) -> None:
        self.changed_files = changed_files

    def status(self) -> IntegrationStatus:
        return IntegrationStatus("getdone", True, True, True, "fake workflow ready")

    def fulfill(self, root: Path, request):
        for relative in self.changed_files:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("generated\n", encoding="utf-8")
        return WorkflowFulfillment(
            CapabilityResultStatus.FULFILLED,
            self.changed_files,
            ("tests passed",),
            "bounded implementation completed",
        )


class MissingWorkflow:
    def status(self) -> IntegrationStatus:
        return IntegrationStatus("getdone", False, False, False, "GetDone is unavailable")

    def fulfill(self, root: Path, request):  # pragma: no cover
        raise AssertionError("must not be called")


def _copy_project(tmp_path: Path) -> Path:
    source = Path(__file__).parents[1]
    root = tmp_path / "project"
    shutil.copytree(
        source,
        root,
        ignore=shutil.ignore_patterns(
            ".pytest_cache", "__pycache__", "capability-results", "build", "dist", "*.egg-info"
        ),
    )
    shutil.copytree(source / "tests/fixtures/runs", root / "runs")
    return root


def test_capability_request_contract_loads() -> None:
    root = Path(__file__).parents[1]
    request = load_capability_request(
        root / "research/capabilities/requests/CAPABILITY-REQUEST-0001.yaml"
    )
    assert request.capability_id == "CAPABILITY-TEMPORAL-DIAGNOSTIC-REPORT-0001"
    assert "runs" in request.scope.forbidden_paths


def test_standalone_missing_workflow_is_explicitly_blocked(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    status = inspect_capability(root, "CAPABILITY-REQUEST-0001", MissingWorkflow())
    assert status["ready_for_delegation"] is False
    result = fulfill_capability(
        root,
        "CAPABILITY-REQUEST-0001",
        attempt_id="missing-provider",
        delegate=MissingWorkflow(),
    )
    payload = json.loads(result.result_path.read_text())
    assert result.status == CapabilityResultStatus.BLOCKED
    assert payload["research_decisions_altered"] is False


def test_compatible_workflow_returns_bounded_immutable_result(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    workflow = FakeWorkflow(changed_files=("src/automo/reports/temporal.py",))
    result = fulfill_capability(
        root,
        "CAPABILITY-REQUEST-0001",
        attempt_id="fulfilled",
        delegate=workflow,
    )
    payload = json.loads(result.result_path.read_text())
    assert payload["status"] == "fulfilled"
    assert payload["changed_files"] == ["src/automo/reports/temporal.py"]
    assert payload["protected_evidence_hashes_before"] == payload["protected_evidence_hashes_after"]
    with pytest.raises(CapabilityLifecycleError, match="already exists"):
        fulfill_capability(
            root,
            "CAPABILITY-REQUEST-0001",
            attempt_id="fulfilled",
            delegate=workflow,
        )


def test_out_of_scope_change_is_rejected(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    with pytest.raises(CapabilityLifecycleError, match="outside capability scope"):
        fulfill_capability(
            root,
            "CAPABILITY-REQUEST-0001",
            attempt_id="bad-scope",
            delegate=FakeWorkflow(changed_files=("src/automo/cli.py",)),
        )


def test_protected_evidence_change_is_rejected(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)

    class MutatingWorkflow(FakeWorkflow):
        def fulfill(self, root: Path, request):
            target = next((root / "runs").rglob("*.json"))
            target.write_text("{}\n", encoding="utf-8")
            return WorkflowFulfillment(CapabilityResultStatus.FULFILLED, (), (), "mutated evidence")

    with pytest.raises(CapabilityLifecycleError, match="altered protected research evidence"):
        fulfill_capability(
            root,
            "CAPABILITY-REQUEST-0001",
            attempt_id="mutated",
            delegate=MutatingWorkflow(),
        )


def test_capability_status_cli_works_without_getdone() -> None:
    root = Path(__file__).parents[1]
    result = CliRunner().invoke(
        app,
        ["capability-status", "CAPABILITY-REQUEST-0001", "--root", str(root)],
    )
    assert result.exit_code == 0
    assert "Ready: no" in result.stdout


def test_fulfilled_result_requires_validation_evidence(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)

    class NoEvidenceWorkflow(FakeWorkflow):
        def fulfill(self, root: Path, request):
            path = root / "docs/generated/report.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("report\n", encoding="utf-8")
            return WorkflowFulfillment(
                CapabilityResultStatus.FULFILLED,
                ("docs/generated/report.md",),
                (),
                "missing evidence",
            )

    with pytest.raises(CapabilityLifecycleError, match="validation evidence"):
        fulfill_capability(
            root,
            "CAPABILITY-REQUEST-0001",
            attempt_id="no-evidence",
            delegate=NoEvidenceWorkflow(),
        )
    assert not (root / "docs/generated/report.md").exists()


def test_status_recovers_persisted_attempt_state(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    fulfill_capability(
        root,
        "CAPABILITY-REQUEST-0001",
        attempt_id="persisted",
        delegate=MissingWorkflow(),
    )
    status = inspect_capability(root, "CAPABILITY-REQUEST-0001", MissingWorkflow())
    assert status["latest_attempt_status"] == "blocked"
    assert status["persisted_attempts"][0]["attempt_id"] == "persisted"
