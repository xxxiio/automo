import json
from pathlib import Path

import pytest

from automo.contracts import load_experiment
from automo.execution import run_temporal_stability
from automo.execution.local import ExecutionError

ROOT = Path(__file__).parents[1]


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "research/experiments").mkdir(parents=True)
    (project / "data").mkdir()
    (project / "research/experiments/EXPERIMENT-0002.yaml").write_bytes(
        (ROOT / "research/experiments/EXPERIMENT-0002.yaml").read_bytes()
    )
    (project / "data/local-fixture.csv").write_bytes((ROOT / "data/local-fixture.csv").read_bytes())
    return project


def test_temporal_stability_executes_only_committed_folds(tmp_path: Path) -> None:
    project = _project(tmp_path)
    experiment = load_experiment(project / "research/experiments/EXPERIMENT-0002.yaml")
    result = run_temporal_stability(project, experiment, run_id="stability")
    payload = json.loads(result.evidence_path.read_text())
    assert payload["trial_order"] == ["FOLD-001", "FOLD-002", "FOLD-003"]
    assert payload["trials_executed"] == 3
    assert payload["committed_folds_only"] is True
    assert payload["arbitrary_trial_search"] is False


def test_temporal_stability_respects_trial_budget(tmp_path: Path) -> None:
    project = _project(tmp_path)
    path = project / "research/experiments/EXPERIMENT-0002.yaml"
    path.write_text(path.read_text().replace("maximum_trials: 3", "maximum_trials: 2"))
    experiment = load_experiment(path)
    with pytest.raises(ExecutionError, match="trial budget"):
        run_temporal_stability(project, experiment, run_id="over-budget")


def test_temporal_stability_is_reproducible_and_immutable(tmp_path: Path) -> None:
    first = _project(tmp_path / "one")
    second = _project(tmp_path / "two")
    exp1 = load_experiment(first / "research/experiments/EXPERIMENT-0002.yaml")
    exp2 = load_experiment(second / "research/experiments/EXPERIMENT-0002.yaml")
    r1 = run_temporal_stability(first, exp1, run_id="same")
    r2 = run_temporal_stability(second, exp2, run_id="same")
    assert json.loads(r1.evidence_path.read_text()) == json.loads(r2.evidence_path.read_text())
    with pytest.raises(ExecutionError, match="immutable"):
        run_temporal_stability(first, exp1, run_id="same")
