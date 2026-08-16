from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from automo.cli import app
from automo.registry import FilesystemModelRegistry, ModelStatus, RegistryError
from automo.runtime import (
    CsvDataSource,
    EvaluationSpec,
    FeatureSetSpec,
    FeatureSpec,
    LambdaFeature,
    MeanSquaredError,
    MetricDirection,
    MetricScope,
    MetricSpec,
    ModelSpec,
    ObjectiveSpec,
    ResearchPlugin,
    ResearchRuntime,
    SingleFeatureLinearRunner,
)


class JsonValueCodec:
    id = "test.json-value-v1"

    def save(self, value: Any, path: Path) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    def load(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))


def _plugin(
    path: Path, *, objective_id: str = "regression", model_id: str = "linear"
) -> ResearchPlugin:
    objective = ObjectiveSpec(objective_id, target="y")
    return ResearchPlugin(
        id="demo",
        data_sources=(CsvDataSource("train", path),),
        feature_computers=(
            LambdaFeature(FeatureSpec("x2", dependencies=("x",)), lambda row, r: float(r["x"]) * 2),
        ),
        feature_sets=(FeatureSetSpec("features", ("x2",)),),
        objectives=(objective,),
        metrics=(MeanSquaredError(),),
        model_specs=(
            ModelSpec(
                id=model_id,
                implementation="linear.single_feature",
                feature_set="features",
                objective=objective,
                evaluation=EvaluationSpec(
                    MetricSpec("mse", MetricDirection.MINIMIZE, MetricScope.LOCAL)
                ),
            ),
        ),
        model_runners=(SingleFeatureLinearRunner(),),
    )


def _runtime(tmp_path: Path, **kwargs: Any) -> ResearchRuntime:
    data = tmp_path / "data.csv"
    data.write_text("x,y\n1,2\n2,4\n3,6\n", encoding="utf-8")
    return ResearchRuntime(_plugin(data, **kwargs))


def test_fit_and_register_captures_complete_lineage_and_loads_model(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    manifest = runtime.fit_and_register(
        "linear",
        data_source_id="train",
        registry=registry,
        registered_model_id="MODEL-000001",
        seed=7,
    )
    assert manifest.id == "MODEL-000001"
    record = registry.get_record(manifest.id)
    assert record.provenance.model_spec_id == "linear"
    assert record.provenance.feature_set_id == "features"
    assert record.provenance.objective_id == "regression"
    assert record.provenance.data_snapshot_hash
    assert record.status is ModelStatus.CANDIDATE
    loaded = registry.load_model(manifest.id)
    assert loaded.predict(({"x2": 8.0},))[0] == pytest.approx(8.0)


def test_benchmarks_append_without_rewriting_manifest(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    manifest = runtime.fit_and_register("linear", data_source_id="train", registry=registry)
    manifest_path = registry.models_root / manifest.id / "manifest.yaml"
    before = manifest_path.read_bytes()
    model = registry.load_model(manifest.id)
    runtime.evaluate_and_record(
        "linear",
        model,
        data_source_id="train",
        registry=registry,
        registered_model_id=manifest.id,
        split="validation",
    )
    registry.append_benchmark(
        manifest.id,
        metric_id="latency_ms",
        direction=MetricDirection.MINIMIZE,
        scope=MetricScope.OPERATIONAL,
        value=1.2,
        sample_count=3,
        split="runtime",
    )
    assert manifest_path.read_bytes() == before
    assert len(registry.benchmarks(manifest.id)) == 2


def test_calibration_has_independent_lineage(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    codec = JsonValueCodec()
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry", calibration_codecs=(codec,))
    model = runtime.fit_and_register("linear", data_source_id="train", registry=registry)
    calibration = registry.register_calibration(
        model.id,
        {"scale": 0.9},
        implementation="test.scale",
        codec=codec,
        calibration_data_snapshot_id="calibration-2026-01",
        calibration_data_snapshot_hash="abc",
        window_start="2026-01-01",
        window_end="2026-01-31",
    )
    assert calibration.base_model_id == model.id
    assert registry.get_manifest(model.id).artifact_hash == model.artifact_hash
    assert registry.get_record(model.id).latest_calibration.id == calibration.id


def test_lifecycle_transitions_are_append_only_and_validated(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    model = runtime.fit_and_register("linear", data_source_id="train", registry=registry)
    registry.transition(model.id, ModelStatus.VALIDATED, reason="validation passed")
    registry.transition(model.id, ModelStatus.ACTIVE, reason="approved for use")
    assert [event.to_status for event in registry.history(model.id)] == [
        ModelStatus.CANDIDATE,
        ModelStatus.VALIDATED,
        ModelStatus.ACTIVE,
    ]
    with pytest.raises(RegistryError, match="illegal lifecycle transition"):
        registry.transition(model.id, ModelStatus.REJECTED, reason="invalid reverse transition")


def test_registry_backend_is_replaceable_without_runtime_api_change(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    delegate = FilesystemModelRegistry(tmp_path / "custom-registry")

    class CustomRegistry:
        def __init__(self) -> None:
            self.called = False

        def register_model(self, model, **kwargs):
            self.called = True
            return delegate.register_model(model, **kwargs)

    custom = CustomRegistry()
    manifest = runtime.fit_and_register("linear", data_source_id="train", registry=custom)  # type: ignore[arg-type]
    assert custom.called is True
    assert manifest.id.startswith("MODEL-")


def test_models_cli_lists_shows_compares_diffs_and_history(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    first = runtime.fit_and_register(
        "linear", data_source_id="train", registry=registry, registered_model_id="MODEL-000001"
    )
    second = runtime.fit_and_register(
        "linear", data_source_id="train", registry=registry, registered_model_id="MODEL-000002"
    )
    registry.transition(first.id, ModelStatus.VALIDATED, reason="validated")
    registry.transition(first.id, ModelStatus.ACTIVE, reason="active")
    registry.append_benchmark(
        first.id,
        metric_id="mse",
        direction=MetricDirection.MINIMIZE,
        scope=MetricScope.LOCAL,
        value=0.0,
        sample_count=3,
        split="oos",
    )
    runner = CliRunner()
    listed = runner.invoke(app, ["models", "list", "--root", str(tmp_path)])
    assert listed.exit_code == 0 and "MODEL-000001" in listed.stdout
    shown = runner.invoke(app, ["models", "show", first.id, "--root", str(tmp_path)])
    assert shown.exit_code == 0 and "Data snapshot:" in shown.stdout
    compared = runner.invoke(
        app, ["models", "compare", first.id, second.id, "--root", str(tmp_path)]
    )
    assert compared.exit_code == 0 and '"objective": "regression"' in compared.stdout
    diffed = runner.invoke(app, ["models", "diff", first.id, second.id, "--root", str(tmp_path)])
    assert diffed.exit_code == 0
    history = runner.invoke(app, ["models", "history", first.id, "--root", str(tmp_path)])
    assert history.exit_code == 0 and "candidate -> validated" in history.stdout
    active = runner.invoke(app, ["models", "active", "--root", str(tmp_path)])
    assert active.exit_code == 0 and first.id in active.stdout and second.id not in active.stdout


def test_compare_rejects_different_objectives(tmp_path: Path) -> None:
    data = tmp_path / "data.csv"
    data.write_text("x,y\n1,2\n2,4\n3,6\n", encoding="utf-8")
    registry = FilesystemModelRegistry(tmp_path / ".automo/registry")
    ResearchRuntime(_plugin(data, objective_id="a", model_id="a-model")).fit_and_register(
        "a-model", data_source_id="train", registry=registry, registered_model_id="MODEL-000001"
    )
    ResearchRuntime(_plugin(data, objective_id="b", model_id="b-model")).fit_and_register(
        "b-model", data_source_id="train", registry=registry, registered_model_id="MODEL-000002"
    )
    result = CliRunner().invoke(
        app, ["models", "compare", "MODEL-000001", "MODEL-000002", "--root", str(tmp_path)]
    )
    assert result.exit_code != 0
    assert "different objectives" in result.stderr
