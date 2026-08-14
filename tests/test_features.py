import hashlib
import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from automo.cli import app
from automo.contracts import FeatureDispositionOutcome
from automo.features import FeatureDispositionError, dispose_local_features

ROOT = Path(__file__).parents[1]
FIXTURE_RUNS = ROOT / "tests/fixtures/runs"


def _copy_run(tmp_path: Path, name: str) -> tuple[Path, Path]:
    project = tmp_path / "project"
    shutil.copytree(ROOT / "research", project / "research")
    run = project / "runs" / name
    shutil.copytree(FIXTURE_RUNS / "experiment-0003-decision", run)
    for filename in ("manifest.json", "decision.json", "freeze.json"):
        path = run / filename
        payload = json.loads(path.read_text())
        payload["run_id"] = name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return project, run


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_positive_feature_group_is_retained_and_decision_unchanged(tmp_path: Path) -> None:
    project, run = _copy_run(tmp_path, "retained")
    decision_before = _sha(run / "decision.json")
    result = dispose_local_features(project, "retained")
    payload = json.loads(result.disposition_path.read_text())
    assert result.outcomes == (("FEATURE-GROUP-CORE-0001", FeatureDispositionOutcome.RETAINED),)
    assert payload["analysis"]["arbitrary_subset_search"] is False
    assert payload["analysis"]["refit_performed"] is False
    assert payload["evidence"]["decision"]["sha256"] == decision_before
    assert _sha(run / "decision.json") == decision_before
    with pytest.raises(FeatureDispositionError, match="immutable"):
        dispose_local_features(project, "retained")


def test_harmful_feature_group_is_rejected(tmp_path: Path) -> None:
    project, run = _copy_run(tmp_path, "rejected-feature")
    for filename in ("validation.json", "out-of-sample.json"):
        path = run / filename
        evidence = json.loads(path.read_text())
        evidence["candidate_mse"] = evidence["baseline_mse"] + 1.0
        evidence["candidate_delta"] = 1.0
        path.write_text(json.dumps(evidence))
    result = dispose_local_features(project, "rejected-feature")
    assert result.outcomes[0][1] is FeatureDispositionOutcome.REJECTED


def test_mixed_feature_effect_is_inconclusive(tmp_path: Path) -> None:
    project, run = _copy_run(tmp_path, "mixed-feature")
    path = run / "out-of-sample.json"
    evidence = json.loads(path.read_text())
    evidence["candidate_mse"] = evidence["baseline_mse"] + 1.0
    evidence["candidate_delta"] = 1.0
    path.write_text(json.dumps(evidence))
    result = dispose_local_features(project, "mixed-feature")
    assert result.outcomes[0][1] is FeatureDispositionOutcome.INCONCLUSIVE


def test_feature_group_limit_blocks_unbounded_analysis(tmp_path: Path) -> None:
    project, _ = _copy_run(tmp_path, "bounded")
    feature_path = project / "research/features/FEATURESET-CORE-0001.yaml"
    feature_path.write_text(feature_path.read_text() + "\n  - id: FEATURE-GROUP-EXTRA\n    description: extra\n    features: [feature_2]\n    ablation_reference: BASELINE-NAIVE-0001\n")
    with pytest.raises(FeatureDispositionError, match="bounded-analysis"):
        dispose_local_features(project, "bounded")


def test_public_cli_reports_feature_disposition(tmp_path: Path) -> None:
    project, _ = _copy_run(tmp_path, "cli-feature")
    result = CliRunner().invoke(app, ["dispose-features", "cli-feature", "--root", str(project)])
    assert result.exit_code == 0, result.output
    assert "FEATURE-GROUP-CORE-0001: retained" in result.output
