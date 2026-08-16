from pathlib import Path

from automo.project import ResearchProject

ROOT = Path(__file__).parents[1]


def test_current_objective_resolves_exact_next_experiment() -> None:
    experiment = ResearchProject(ROOT).next_experiment()
    assert experiment.identifier == "EXPERIMENT-0002"
    assert experiment.objective == "OBJECTIVE-0001"
