from pathlib import Path

import pytest

from automo.contracts import ContractError, ExperimentStatus, load_experiment


ROOT = Path(__file__).parents[1]


def test_sample_experiment_loads() -> None:
    experiment = load_experiment(ROOT / "research/experiments/EXPERIMENT-0001.yaml")
    assert experiment.identifier == "EXPERIMENT-0001"
    assert experiment.status is ExperimentStatus.READY
    assert experiment.maximum_trials == 3
    assert experiment.falsification


def test_missing_falsification_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "experiment.yaml"
    path.write_text("id: EXPERIMENT-1\n", encoding="utf-8")
    with pytest.raises(ContractError, match="missing required keys"):
        load_experiment(path)
