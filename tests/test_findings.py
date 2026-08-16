import hashlib
import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from automo.cli import app
from automo.findings import FindingError, propose_next_experiment

ROOT = Path(__file__).parents[1]
FIXTURE_RUNS = ROOT / "tests/fixtures/runs"


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(
            ".pytest_cache", "__pycache__", "build", "dist", "*.egg-info"
        ),
    )
    shutil.copytree(FIXTURE_RUNS, root / "runs")
    (root / "research/experiments/EXPERIMENT-0002.yaml").unlink(missing_ok=True)
    (root / "runs/experiment-0004-features/findings.json").unlink(missing_ok=True)
    return root


def test_proposes_exactly_one_falsifiable_experiment_without_mutating_evidence(tmp_path):
    root = _project(tmp_path)
    run = root / "runs" / "experiment-0004-features"
    before = {
        name: hashlib.sha256((run / name).read_bytes()).hexdigest()
        for name in ("decision.json", "feature-dispositions.json")
    }
    result = propose_next_experiment(root, "experiment-0004-features")
    findings = json.loads(result.findings_path.read_text())
    assert findings["next_experiment"]["count"] == 1
    assert len(findings["next_experiment"]["falsification"]) >= 1
    assert result.next_experiment_path.exists()
    after = {name: hashlib.sha256((run / name).read_bytes()).hexdigest() for name in before}
    assert before == after


def test_findings_are_immutable(tmp_path):
    root = _project(tmp_path)
    propose_next_experiment(root, "experiment-0004-features")
    with pytest.raises(FindingError):
        propose_next_experiment(root, "experiment-0004-features")


def test_cli_propose_next(tmp_path):
    root = _project(tmp_path)
    result = CliRunner().invoke(
        app, ["propose-next", "experiment-0004-features", "--root", str(root)]
    )
    assert result.exit_code == 0
    assert "Next experiment: EXPERIMENT-0002" in result.stdout
