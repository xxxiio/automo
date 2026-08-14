"""Project repository conventions for committed research state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from automo.contracts import ContractError, ExperimentSpec, ResearchObjective, load_experiment, load_objective


@dataclass(frozen=True)
class ResearchProject:
    root: Path

    @property
    def objective_path(self) -> Path:
        return self.root / "research" / "objectives" / "current.yaml"

    def objective(self) -> ResearchObjective:
        return load_objective(self.objective_path)

    def next_experiment(self) -> ExperimentSpec:
        objective = self.objective()
        path = self.root / "research" / "experiments" / f"{objective.next_experiment}.yaml"
        experiment = load_experiment(path)
        if experiment.identifier != objective.next_experiment:
            raise ContractError(
                f"next experiment pointer {objective.next_experiment!r} does not match "
                f"contract id {experiment.identifier!r}"
            )
        if experiment.objective != objective.identifier:
            raise ContractError(
                f"experiment objective {experiment.objective!r} does not match "
                f"current objective {objective.identifier!r}"
            )
        return experiment
