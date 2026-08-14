import json
import shutil
from pathlib import Path

import pytest

from automo.contracts import DecisionOutcome
from automo.decisions import DecisionError, decide_local_run

ROOT = Path(__file__).parents[1]
FIXTURE_RUNS = ROOT / "tests/fixtures/runs"


def _copy_completed_run(tmp_path: Path, name: str = "run") -> tuple[Path, Path]:
    project = tmp_path / "project"
    shutil.copytree(ROOT / "research", project / "research")
    run = project / "runs" / name
    shutil.copytree(FIXTURE_RUNS / "experiment-0002-freeze", run)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["run_id"] = name
    manifest["decision_policy"] = "POLICY-REPRODUCIBILITY-FIRST-0001"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return project, run


def test_completed_run_produces_one_accepted_decision(tmp_path: Path) -> None:
    project, run = _copy_completed_run(tmp_path, "accepted")
    result = decide_local_run(project, "accepted")
    payload = json.loads(result.decision_path.read_text())
    assert result.outcome is DecisionOutcome.ACCEPTED
    assert payload["refit_performed"] is False
    assert payload["evidence"]["validation"]["sha256"]
    assert payload["evidence"]["out_of_sample"]["sha256"]
    with pytest.raises(DecisionError, match="immutable"):
        decide_local_run(project, "accepted")


def test_failed_oos_gate_is_rejected(tmp_path: Path) -> None:
    project, run = _copy_completed_run(tmp_path, "rejected")
    oos = json.loads((run / "out-of-sample.json").read_text())
    oos["candidate_delta"] = 1.0
    (run / "out-of-sample.json").write_text(json.dumps(oos))
    result = decide_local_run(project, "rejected")
    assert result.outcome is DecisionOutcome.REJECTED


def test_insufficient_evidence_is_inconclusive(tmp_path: Path) -> None:
    project, run = _copy_completed_run(tmp_path, "inconclusive")
    validation = json.loads((run / "validation.json").read_text())
    validation["observations"] = 1
    (run / "validation.json").write_text(json.dumps(validation))
    result = decide_local_run(project, "inconclusive")
    assert result.outcome is DecisionOutcome.INCONCLUSIVE


def test_malformed_evidence_is_invalid(tmp_path: Path) -> None:
    project, run = _copy_completed_run(tmp_path, "invalid")
    validation = json.loads((run / "validation.json").read_text())
    del validation["candidate_delta"]
    (run / "validation.json").write_text(json.dumps(validation))
    result = decide_local_run(project, "invalid")
    assert result.outcome is DecisionOutcome.INVALID
