from pathlib import Path

from automo.contracts import load_experiment
from automo.prerequisites import (
    BlockerType,
    DataAvailability,
    MappingDataCatalogue,
    SetCapabilityCatalogue,
    validate_prerequisites,
)


ROOT = Path(__file__).parents[1]
EXPERIMENT = load_experiment(ROOT / "research/experiments/EXPERIMENT-0001.yaml")


def test_unavailable_data_is_a_user_action_blocker() -> None:
    report = validate_prerequisites(
        EXPERIMENT,
        MappingDataCatalogue({}),
        SetCapabilityCatalogue(set()),
    )
    assert not report.ready
    assert report.blockers[0].type is BlockerType.UNAVAILABLE_DATA_SOURCE
    assert "Provide or approve access" in report.blockers[0].user_action_required


def test_ready_when_data_and_capabilities_are_available() -> None:
    report = validate_prerequisites(
        EXPERIMENT,
        MappingDataCatalogue(
            {
                "DATASET-LOCAL-FIXTURE-0001": DataAvailability(
                    True,
                    frozenset({"timestamp", "entity_id", "target", "feature_1"}),
                    "2020-01-01",
                    "2024-12-31",
                )
            }
        ),
        SetCapabilityCatalogue(
            {"CAPABILITY-TIME-AWARE-SPLIT-0001", "CAPABILITY-LINEAR-RUNNER-0001"}
        ),
    )
    assert report.ready
