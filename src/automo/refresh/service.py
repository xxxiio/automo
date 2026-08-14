from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from automo.persistence import write_json_artifact
from automo.registry import FilesystemModelRegistry, ModelStatus
from automo.runtime.contracts import MetricDirection
from automo.runtime.project import ResearchRuntime

from .contracts import (
    Calibrator,
    DataIteration,
    EvaluationPartitions,
    ModelPoolSnapshot,
    ModelPoolSpec,
    ModelRefreshDisposition,
    RefreshAction,
    RefreshError,
    RefreshScoreCard,
    SelectionKind,
    SplitStrategy,
)
from .pool import FilesystemPoolStore


def _rows(rows: Sequence[Mapping[str, Any]], indices: tuple[int, ...]) -> tuple[Mapping[str, Any], ...]:
    return tuple(rows[i] for i in indices)


def _better(a: float, b: float, direction: MetricDirection) -> bool:
    return a > b if direction == MetricDirection.MAXIMIZE else a < b


class RefreshService:
    def __init__(
        self,
        runtime: ResearchRuntime,
        registry: FilesystemModelRegistry,
        pool_store: FilesystemPoolStore,
        *,
        calibrators: Sequence[Calibrator] = (),
        refresh_root: Path | None = None,
    ) -> None:
        self.runtime = runtime
        self.registry = registry
        self.pool_store = pool_store
        self.calibrators = {item.id: item for item in calibrators}
        self.refresh_root = refresh_root or pool_store.root.parent / "refresh"
        self.refresh_root.mkdir(parents=True, exist_ok=True)

    def _materialize(self, model_spec_id: str, rows: Sequence[Mapping[str, Any]]):
        spec = self.runtime.model_specs[model_spec_id]
        fs = self.runtime.feature_sets[spec.feature_set]
        materialized = self.runtime.features.materialize(tuple(rows), fs)
        truth = tuple(float(row[spec.objective.target]) for row in rows)
        return spec, materialized, truth

    def _evaluate_model(self, model_spec_id: str, model: Any, rows: Sequence[Mapping[str, Any]], calibration: Any | None = None) -> dict[str, float]:
        spec, materialized, truth = self._materialize(model_spec_id, rows)
        prediction = tuple(float(v) for v in model.predict(materialized))
        if calibration is not None:
            prediction = tuple(float(v) for v in calibration.transform(prediction))
        metrics = (spec.evaluation.primary, *spec.evaluation.secondary)
        return {m.id: self.runtime.metrics[m.id].evaluate(truth, prediction) for m in metrics}

    def _fit_calibration(self, pool: ModelPoolSpec, model: Any, fit_rows: Sequence[Mapping[str, Any]]):
        calibrator_id = pool.calibration_policy.calibrator
        if not calibrator_id:
            return None, None
        try:
            calibrator = self.calibrators[calibrator_id]
        except KeyError as exc:
            raise RefreshError(f"unknown calibrator: {calibrator_id}") from exc
        spec, materialized, truth = self._materialize(pool.model_spec_id, fit_rows)
        prediction = model.predict(materialized)
        return calibrator, calibrator.fit(prediction, truth)

    def _record_scorecard(self, pool: ModelPoolSpec, card: RefreshScoreCard) -> None:
        spec = self.runtime.model_specs[pool.model_spec_id]
        metric_specs = {m.id: m for m in (spec.evaluation.primary, *spec.evaluation.secondary)}
        for split_name, values, count in (
            ("refresh_validation", card.validation_metrics, card.validation_count),
            ("refresh_oos", card.test_metrics, card.test_count),
        ):
            for metric_id, value in values.items():
                contract = metric_specs[metric_id]
                self.registry.append_benchmark(
                    card.model_id, metric_id=metric_id, direction=contract.direction, scope=contract.scope,
                    value=value, sample_count=count, split=split_name, calibration_id=card.calibration_id,
                )

    @staticmethod
    def _validation_test_degradation(card: RefreshScoreCard, metric: str, direction: MetricDirection) -> float:
        validation = card.validation_metrics[metric]
        test = card.test_metrics[metric]
        return (test - validation) if direction == MetricDirection.MINIMIZE else (validation - test)

    def plan(self, pool: ModelPoolSpec, iteration: DataIteration, split: SplitStrategy, *, data_source_id: str) -> dict[str, Any]:
        snapshot = self.runtime.data_sources[data_source_id].snapshot()
        if snapshot.id != iteration.snapshot_id or snapshot.content_hash != iteration.snapshot_hash:
            raise RefreshError("data iteration does not match current data snapshot")
        partitions = split.split(snapshot)
        active = [r for r in self.registry.list_models() if r.manifest.objective_id == pool.objective_id and r.status in {ModelStatus.ACTIVE, ModelStatus.VALIDATED, ModelStatus.DEGRADED}]
        return {
            "iteration_id": iteration.id,
            "pool_id": pool.id,
            "split_strategy": split.id,
            "counts": {"fit": len(partitions.fit.row_indices), "validation": len(partitions.validation.row_indices), "test": len(partitions.test.row_indices)},
            "models": [r.manifest.id for r in active],
            "recalibration_planned": bool(pool.calibration_policy.each_iteration and pool.calibration_policy.calibrator),
            "retraining_planned": bool(pool.training_policy.each_iteration),
        }

    def run(self, pool: ModelPoolSpec, iteration: DataIteration, split: SplitStrategy, *, data_source_id: str, dry_run: bool = False) -> dict[str, Any]:
        snapshot = self.runtime.data_sources[data_source_id].snapshot()
        if snapshot.id != iteration.snapshot_id or snapshot.content_hash != iteration.snapshot_hash:
            raise RefreshError("data iteration does not match current data snapshot")
        partitions = split.split(snapshot)
        fit_rows = _rows(snapshot.rows, partitions.fit.row_indices)
        validation_rows = _rows(snapshot.rows, partitions.validation.row_indices)
        test_rows = _rows(snapshot.rows, partitions.test.row_indices)
        if dry_run:
            return self.plan(pool, iteration, split, data_source_id=data_source_id)
        directory = self.refresh_root / iteration.id
        if directory.exists():
            raise RefreshError(f"refresh iteration already exists: {iteration.id}")
        directory.mkdir(parents=True)

        records = [r for r in self.registry.list_models() if r.manifest.objective_id == pool.objective_id and r.status in {ModelStatus.ACTIVE, ModelStatus.VALIDATED, ModelStatus.DEGRADED}]
        scorecards: list[RefreshScoreCard] = []
        dispositions: list[ModelRefreshDisposition] = []

        for record in records:
            model = self.registry.load_model(record.manifest.id)
            base_val = self._evaluate_model(pool.model_spec_id, model, validation_rows)
            base_test = self._evaluate_model(pool.model_spec_id, model, test_rows)
            chosen_calibration = None
            chosen_calibration_id = None
            action = RefreshAction.KEEP
            reasons = ["existing model evaluated on validation and refresh-OOS"]

            if pool.calibration_policy.each_iteration and len(fit_rows) >= pool.calibration_policy.min_fit_observations and pool.calibration_policy.calibrator:
                calibrator, candidate_calibration = self._fit_calibration(pool, model, fit_rows)
                candidate_val = self._evaluate_model(pool.model_spec_id, model, validation_rows, candidate_calibration)
                metric = pool.primary_metric_id
                if _better(candidate_val[metric], base_val[metric], pool.primary_metric_direction):
                    chosen_calibration = candidate_calibration
                    candidate_test = self._evaluate_model(pool.model_spec_id, model, test_rows, candidate_calibration)
                    manifest = self.registry.register_calibration(
                        record.manifest.id,
                        candidate_calibration,
                        implementation=calibrator.id,
                        codec=calibrator.artifact_codec,
                        calibration_data_snapshot_id=iteration.snapshot_id,
                        calibration_data_snapshot_hash=iteration.snapshot_hash,
                    )
                    chosen_calibration_id = manifest.id
                    base_val, base_test = candidate_val, candidate_test
                    action = RefreshAction.RECALIBRATE
                    reasons.append("candidate recalibration improved validation before refresh-OOS evaluation")
                else:
                    reasons.append("candidate recalibration rejected on validation; refresh-OOS remained untouched for that variant")

            card = RefreshScoreCard(
                model_id=record.manifest.id,
                calibration_id=chosen_calibration_id,
                validation_metrics=base_val,
                test_metrics=base_test,
                validation_count=len(validation_rows),
                test_count=len(test_rows),
                source="existing",
            )
            scorecards.append(card)
            self._record_scorecard(pool, card)
            dispositions.append(ModelRefreshDisposition(record.manifest.id, action, tuple(reasons), calibration_id=chosen_calibration_id))

        if pool.training_policy.each_iteration and len(fit_rows) >= pool.training_policy.min_new_observations:
            spec, materialized, truth = self._materialize(pool.model_spec_id, fit_rows)
            runner = self.runtime.model_runners[spec.implementation]
            fitted = runner.fit(spec, materialized, target=truth)
            candidate_val = self._evaluate_model(pool.model_spec_id, fitted, validation_rows)
            metric = pool.primary_metric_id
            incumbent_best = min(scorecards, key=lambda s: s.validation_metrics[metric]) if pool.primary_metric_direction == MetricDirection.MINIMIZE and scorecards else max(scorecards, key=lambda s: s.validation_metrics[metric]) if scorecards else None
            if incumbent_best is None or _better(candidate_val[metric], incumbent_best.validation_metrics[metric], pool.primary_metric_direction):
                codec = getattr(runner, "artifact_codec", None)
                if codec is None:
                    raise RefreshError("runner must expose artifact_codec for refresh retraining")
                from automo.registry import TrainingProvenance
                import platform
                provenance = TrainingProvenance(
                    data_source_id=data_source_id,
                    data_snapshot_id=snapshot.id,
                    data_snapshot_hash=snapshot.content_hash,
                    feature_set_id=spec.feature_set,
                    model_spec_id=spec.id,
                    objective_id=spec.objective.id,
                    runner_implementation=spec.implementation,
                    python_version=platform.python_version(),
                )
                manifest = self.registry.register_model(
                    fitted,
                    implementation=spec.implementation,
                    model_spec_id=spec.id,
                    objective_id=spec.objective.id,
                    feature_set_id=spec.feature_set,
                    provenance=provenance,
                    codec=codec,
                )
                test_metrics = self._evaluate_model(pool.model_spec_id, fitted, test_rows)
                card = RefreshScoreCard(manifest.id, None, candidate_val, test_metrics, len(validation_rows), len(test_rows), source="retrained")
                scorecards.append(card)
                self._record_scorecard(pool, card)
                dispositions.append(ModelRefreshDisposition(manifest.id, RefreshAction.RETRAIN, ("retrained candidate improved validation before refresh-OOS evaluation",), replacement_model_id=manifest.id))

        metric = pool.primary_metric_id
        eligible = []
        for card in scorecards:
            if card.test_count < pool.retention_policy.minimum_test_observations:
                continue
            maximum = pool.retention_policy.maximum_validation_test_degradation
            if maximum is not None and self._validation_test_degradation(card, metric, pool.primary_metric_direction) > maximum:
                dispositions.append(ModelRefreshDisposition(card.model_id, RefreshAction.DEGRADE, ("validation-to-refresh-OOS degradation exceeded retention policy",), calibration_id=card.calibration_id))
                continue
            eligible.append(card)
        eligible.sort(key=lambda card: card.test_metrics[metric], reverse=pool.primary_metric_direction == MetricDirection.MAXIMIZE)
        retained = eligible[: pool.retention_policy.top_k]
        active_ids = tuple(card.model_id for card in retained)

        for record in self.registry.list_models():
            if record.manifest.objective_id != pool.objective_id:
                continue
            if record.manifest.id in active_ids:
                if record.status == ModelStatus.CANDIDATE:
                    self.registry.transition(record.manifest.id, ModelStatus.VALIDATED, reason=f"retained by refresh {iteration.id}")
                    self.registry.transition(record.manifest.id, ModelStatus.ACTIVE, reason=f"admitted to pool {pool.id}")
                elif record.status == ModelStatus.VALIDATED:
                    self.registry.transition(record.manifest.id, ModelStatus.ACTIVE, reason=f"admitted to pool {pool.id}")
                elif record.status == ModelStatus.DEGRADED:
                    self.registry.transition(record.manifest.id, ModelStatus.ACTIVE, reason=f"restored by refresh {iteration.id}")
            elif record.status == ModelStatus.ACTIVE:
                self.registry.transition(record.manifest.id, ModelStatus.DEGRADED, reason=f"not retained by refresh {iteration.id}")

        if pool.selection_policy.kind == SelectionKind.RECENT_BEST:
            selected_ids = active_ids[:1]
        else:
            def overall_value(card: RefreshScoreCard) -> float:
                observations = [b.value for b in self.registry.benchmarks(card.model_id) if b.metric_id == metric and b.split == "refresh_oos"]
                return sum(observations) / len(observations) if observations else card.test_metrics[metric]
            overall = sorted(retained, key=overall_value, reverse=pool.primary_metric_direction == MetricDirection.MAXIMIZE)
            selected_ids = tuple(card.model_id for card in overall[:1])
        pool_snapshot = ModelPoolSnapshot(pool.id, iteration.id, active_ids, selected_ids, tuple(scorecards))
        snapshot_path = self.pool_store.save_snapshot(pool_snapshot)

        report = {
            "iteration": asdict(iteration),
            "split_strategy": split.id,
            "partition_counts": {"fit": len(fit_rows), "validation": len(validation_rows), "test": len(test_rows)},
            "scorecards": [asdict(x) for x in scorecards],
            "dispositions": [asdict(x) for x in dispositions],
            "retained_model_ids": list(active_ids),
            "selected_model_ids": list(selected_ids),
            "pool_snapshot": str(snapshot_path),
            "refresh_oos_used_only_after_variant_freeze": True,
        }
        path = directory / "report.json"
        write_json_artifact(path, artifact_type="automo.refresh_report", payload=report)
        return report
