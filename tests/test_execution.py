import json
from pathlib import Path

import pytest

from automo.contracts import load_experiment
from automo.execution import run_local_experiment
from automo.execution.local import ExecutionError

ROOT = Path(__file__).parents[1]


def test_local_experiment_is_reproducible(tmp_path: Path) -> None:
    experiment = load_experiment(ROOT / "research/experiments/EXPERIMENT-0001.yaml")
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    for target in (first_root, second_root):
        (target / "research/experiments").mkdir(parents=True)
        (target / "data").mkdir()
        (target / "research/experiments/EXPERIMENT-0001.yaml").write_bytes(
            (ROOT / "research/experiments/EXPERIMENT-0001.yaml").read_bytes()
        )
        (target / "data/local-fixture.csv").write_bytes(
            (ROOT / "data/local-fixture.csv").read_bytes()
        )
    first = run_local_experiment(first_root, experiment, run_id="run-one")
    second = run_local_experiment(second_root, experiment, run_id="run-two")
    assert first.configuration_fingerprint == second.configuration_fingerprint
    assert json.loads(first.validation_path.read_text()) == json.loads(
        second.validation_path.read_text()
    )
    assert json.loads(first.out_of_sample_path.read_text()) == json.loads(
        second.out_of_sample_path.read_text()
    )


def test_validation_and_oos_are_separate_and_manifested(tmp_path: Path) -> None:
    experiment = load_experiment(ROOT / "research/experiments/EXPERIMENT-0001.yaml")
    project = tmp_path / "project"
    (project / "research/experiments").mkdir(parents=True)
    (project / "data").mkdir()
    (project / "research/experiments/EXPERIMENT-0001.yaml").write_bytes(
        (ROOT / "research/experiments/EXPERIMENT-0001.yaml").read_bytes()
    )
    (project / "data/local-fixture.csv").write_bytes((ROOT / "data/local-fixture.csv").read_bytes())
    result = run_local_experiment(project, experiment, run_id="separate-evidence")
    manifest = json.loads(result.manifest_path.read_text())
    assert result.validation_path != result.out_of_sample_path
    assert manifest["evidence"] == {
        "out_of_sample": "out-of-sample.json",
        "validation": "validation.json",
    }
    assert manifest["seed"] == 42
    assert manifest["compute_cost"] == 0.0
    assert manifest["code"]["experiment_sha256"]
    assert manifest["data"]["snapshot_sha256"]


def test_run_directory_is_immutable(tmp_path: Path) -> None:
    experiment = load_experiment(ROOT / "research/experiments/EXPERIMENT-0001.yaml")
    project = tmp_path / "project"
    (project / "research/experiments").mkdir(parents=True)
    (project / "data").mkdir()
    (project / "research/experiments/EXPERIMENT-0001.yaml").write_bytes(
        (ROOT / "research/experiments/EXPERIMENT-0001.yaml").read_bytes()
    )
    (project / "data/local-fixture.csv").write_bytes((ROOT / "data/local-fixture.csv").read_bytes())
    run_local_experiment(project, experiment, run_id="immutable")
    with pytest.raises(ExecutionError, match="immutable"):
        run_local_experiment(project, experiment, run_id="immutable")


def _copy_experiment_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "research/experiments").mkdir(parents=True)
    (project / "data").mkdir()
    (project / "research/experiments/EXPERIMENT-0001.yaml").write_bytes(
        (ROOT / "research/experiments/EXPERIMENT-0001.yaml").read_bytes()
    )
    (project / "data/local-fixture.csv").write_bytes((ROOT / "data/local-fixture.csv").read_bytes())
    return project


def test_oos_requires_a_freeze_artifact(tmp_path: Path) -> None:
    from automo.execution import evaluate_local_out_of_sample

    project = _copy_experiment_project(tmp_path)
    (project / "runs/unfrozen").mkdir(parents=True)
    with pytest.raises(ExecutionError, match="requires a valid freeze"):
        evaluate_local_out_of_sample(project, "unfrozen")


def test_post_freeze_dataset_change_is_rejected(tmp_path: Path) -> None:
    from automo.execution import evaluate_local_out_of_sample, prepare_local_experiment

    experiment = load_experiment(ROOT / "research/experiments/EXPERIMENT-0001.yaml")
    project = _copy_experiment_project(tmp_path)
    prepared = prepare_local_experiment(project, experiment, run_id="frozen-dataset")
    with (project / "data/local-fixture.csv").open("a", encoding="utf-8") as stream:
        stream.write("2024-12-31,Z,99,99\n")
    with pytest.raises(ExecutionError, match="post-freeze configuration change detected: dataset"):
        evaluate_local_out_of_sample(project, prepared.run_id)


def test_post_freeze_experiment_change_is_rejected(tmp_path: Path) -> None:
    from automo.execution import evaluate_local_out_of_sample, prepare_local_experiment

    experiment = load_experiment(ROOT / "research/experiments/EXPERIMENT-0001.yaml")
    project = _copy_experiment_project(tmp_path)
    prepared = prepare_local_experiment(project, experiment, run_id="frozen-experiment")
    experiment_path = project / "research/experiments/EXPERIMENT-0001.yaml"
    experiment_path.write_text(experiment_path.read_text() + "\n# changed after freeze\n")
    with pytest.raises(
        ExecutionError, match="post-freeze configuration change detected: experiment"
    ):
        evaluate_local_out_of_sample(project, prepared.run_id)


def test_unchanged_freeze_produces_oos_evidence(tmp_path: Path) -> None:
    from automo.execution import evaluate_local_out_of_sample, prepare_local_experiment

    experiment = load_experiment(ROOT / "research/experiments/EXPERIMENT-0001.yaml")
    project = _copy_experiment_project(tmp_path)
    prepared = prepare_local_experiment(project, experiment, run_id="sealed")
    assert prepared.freeze_path.exists()
    assert not (prepared.run_directory / "out-of-sample.json").exists()
    completed = evaluate_local_out_of_sample(project, prepared.run_id)
    manifest = json.loads(completed.manifest_path.read_text())
    assert completed.out_of_sample_path.exists()
    assert manifest["freeze"]["path"] == "freeze.json"
    assert manifest["evidence"]["out_of_sample"] == "out-of-sample.json"
