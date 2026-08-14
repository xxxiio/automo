from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from automo.persistence import write_yaml_artifact
from automo.refresh.contracts import SplitStrategy
from automo.runtime.contracts import EvaluationContext, MetricDirection, ModelOutputBatch, ModelSpec, PredictionRequest, TrainingRequest
from automo.runtime.project import ResearchRuntime
from automo.runtime.graph import LegacyPredictorAdapter

from .contracts import (
    CandidateProposal,
    CandidateResult,
    CandidateStage,
    InterventionKind,
    ResearchBudget,
    ResearchIntervention,
    ResearchIterationReport,
    ResearchPlan,
    ResearchSafeguards,
    ResearchSearchSpace,
)
from .store import FilesystemResearchStore


class ResearchError(RuntimeError):
    pass


_DIAGNOSIS_ORDER: Mapping[str, tuple[InterventionKind, ...]] = {
    "poor_calibration": (InterventionKind.CALIBRATION,),
    "overfitting": (InterventionKind.PARAMETERS, InterventionKind.FEATURE_SET),
    "underfitting": (InterventionKind.MODEL, InterventionKind.FEATURE_SET, InterventionKind.PARAMETERS),
    "feature_gap": (InterventionKind.FEATURE_SET,),
    "feature_redundancy": (InterventionKind.FEATURE_SET,),
    "training_staleness": (InterventionKind.TRAINING_WINDOW,),
}


class ResearchService:
    def __init__(
        self,
        runtime: ResearchRuntime,
        *,
        split_strategies: Sequence[SplitStrategy],
        store: FilesystemResearchStore,
        registry: Any | None = None,
    ) -> None:
        self.runtime = runtime
        self.splits = {item.id: item for item in split_strategies}
        self.store = store
        self.registry = registry

    def plan(
        self,
        *,
        iteration_id: str,
        baseline_model_spec_id: str,
        data_source_id: str,
        split_strategy_id: str,
        diagnosis: str,
        findings: Sequence[str],
        search_space: ResearchSearchSpace,
        budget: ResearchBudget,
        safeguards: ResearchSafeguards,
    ) -> ResearchPlan:
        if baseline_model_spec_id not in self.runtime.model_specs:
            raise ResearchError(f"unknown baseline model spec: {baseline_model_spec_id}")
        if data_source_id not in self.runtime.data_sources:
            raise ResearchError(f"unknown data source: {data_source_id}")
        if split_strategy_id not in self.splits:
            raise ResearchError(f"unknown split strategy: {split_strategy_id}")
        proposals = self._generate_candidates(baseline_model_spec_id, diagnosis, findings, search_space)
        prior = self.store.fingerprints()
        proposals = tuple(item for item in proposals if item.fingerprint not in prior)[: budget.maximum_candidates]
        if not proposals:
            raise ResearchError("no untested candidates remain within the committed search space")
        plan = ResearchPlan(
            id=iteration_id,
            baseline_model_spec_id=baseline_model_spec_id,
            data_source_id=data_source_id,
            split_strategy_id=split_strategy_id,
            diagnosis=diagnosis,
            findings=tuple(findings),
            search_space=search_space,
            budget=budget,
            safeguards=safeguards,
            candidates=proposals,
        )
        self.store.create_plan(plan)
        return plan

    def execute(self, plan: ResearchPlan) -> ResearchIterationReport:
        snapshot = self.runtime.data_sources[plan.data_source_id].snapshot()
        partitions = self.splits[plan.split_strategy_id].split(snapshot)
        if len(partitions.validation.row_indices) < plan.safeguards.minimum_validation_observations:
            raise ResearchError("validation partition is below the committed minimum observation count")
        if len(partitions.test.row_indices) < plan.safeguards.minimum_oos_observations:
            raise ResearchError("OOS partition is below the committed minimum observation count")
        fit_rows = self._rows(snapshot.rows, partitions.fit.row_indices)
        validation_rows = self._rows(snapshot.rows, partitions.validation.row_indices)
        test_rows = self._rows(snapshot.rows, partitions.test.row_indices)
        baseline_spec = self.runtime.model_specs[plan.baseline_model_spec_id]
        baseline_model = self._fit_spec(baseline_spec, fit_rows)
        baseline_validation = self._primary_metric(baseline_spec, baseline_model, validation_rows)
        baseline_oos = self._primary_metric(baseline_spec, baseline_model, test_rows)

        validation_trials = 0
        fit_count = 1
        staged: list[tuple[CandidateProposal, ModelSpec, Any, float, Any | None, str | None]] = []
        rejected: list[CandidateResult] = []
        for proposal in plan.candidates:
            if validation_trials >= plan.budget.maximum_candidates or fit_count >= plan.budget.maximum_model_fits:
                break
            try:
                candidate_spec, model, calibration, calibration_id = self._fit_candidate(proposal, baseline_spec, fit_rows)
            except ResearchError as exc:
                self._persist_capability_request(plan, proposal, str(exc))
                rejected.append(CandidateResult(proposal.id, proposal.fingerprint, CandidateStage.BLOCKED, reason=str(exc)))
                continue
            fit_count += 1
            validation_trials += 1
            validation_value = self._primary_metric(candidate_spec, model, validation_rows, calibration=calibration)
            improvement = self._improvement(candidate_spec.evaluation.primary.direction, baseline_validation, validation_value)
            if improvement + 1e-15 < plan.safeguards.minimum_improvement:
                rejected.append(CandidateResult(
                    proposal.id, proposal.fingerprint, CandidateStage.REJECTED,
                    validation_metric=validation_value,
                    baseline_validation_metric=baseline_validation,
                    validation_count=len(validation_rows),
                    reason="candidate failed minimum validation improvement",
                ))
                continue
            staged.append((proposal, candidate_spec, model, validation_value, calibration, calibration_id))

        direction = baseline_spec.evaluation.primary.direction
        staged.sort(key=lambda row: row[3], reverse=direction == MetricDirection.MAXIMIZE)
        shortlist = staged[: plan.budget.maximum_oos_candidates]
        results = list(rejected)
        oos_trials = 0
        for proposal, candidate_spec, model, validation_value, calibration, calibration_id in shortlist:
            oos_trials += 1
            oos_value = self._primary_metric(candidate_spec, model, test_rows, calibration=calibration)
            improvement = self._improvement(direction, baseline_oos, oos_value)
            accepted = improvement + 1e-15 >= plan.safeguards.minimum_improvement
            registered_id = None
            if accepted and self.registry is not None and calibration is None:
                registered_id = self._register_candidate(candidate_spec, model, plan.data_source_id, proposal)
            results.append(CandidateResult(
                proposal.id,
                proposal.fingerprint,
                CandidateStage.ACCEPTED if accepted else CandidateStage.REJECTED,
                validation_metric=validation_value,
                oos_metric=oos_value,
                baseline_validation_metric=baseline_validation,
                baseline_oos_metric=baseline_oos,
                validation_count=len(validation_rows),
                oos_count=len(test_rows),
                registered_model_id=registered_id,
                calibration_id=calibration_id,
                reason="sealed research OOS gate passed" if accepted else "sealed research OOS gate failed",
            ))
        report = ResearchIterationReport(
            id=plan.id,
            plan_id=plan.id,
            proposals_count=len(plan.candidates),
            validation_trials=validation_trials,
            oos_trials=oos_trials,
            repeated_validation_exposure=len(plan.candidates),
            results=tuple(sorted(results, key=lambda x: x.candidate_id)),
        )
        self.store.write_report(report)
        return report


    def _persist_capability_request(self, plan: ResearchPlan, proposal: CandidateProposal, reason: str) -> None:
        if "missing capability:" not in reason:
            return
        capability = reason.split("missing capability:", 1)[1].strip()
        request_id = f"CAPABILITY-{plan.id}-{proposal.id}"
        root = self.store.root.parent.parent / "research" / "capabilities" / "requests"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{request_id}.yaml"
        if path.exists():
            return
        payload = {
            "id": request_id,
            "experiment": plan.id,
            "capability": {"id": capability.replace(" ", "-"), "kind": "research-runtime"},
            "reason": reason,
            "contract": {"inputs": [proposal.baseline_model_spec_id], "outputs": [capability]},
            "requirements": ["implementation must satisfy the registered Automo runtime protocol"],
            "acceptance": ["tests pass", "research evidence remains unchanged"],
            "scope": {
                "allowed_paths": ["src", "tests", "automo.toml"],
                "forbidden_paths": ["runs", "recommendations", ".automo/research"],
            },
        }
        write_yaml_artifact(path, artifact_type="automo.capability_request", payload=payload)

    def _generate_candidates(self, baseline_id: str, diagnosis: str, findings: Sequence[str], space: ResearchSearchSpace) -> tuple[CandidateProposal, ...]:
        allowed = _DIAGNOSIS_ORDER.get(diagnosis, (InterventionKind.MODEL, InterventionKind.FEATURE_SET, InterventionKind.CALIBRATION, InterventionKind.PARAMETERS))
        values: list[ResearchIntervention] = []
        if InterventionKind.CALIBRATION in allowed:
            values.extend(ResearchIntervention(InterventionKind.CALIBRATION, {"calibrator_id": value}) for value in space.calibrator_ids)
        if InterventionKind.FEATURE_SET in allowed:
            values.extend(ResearchIntervention(InterventionKind.FEATURE_SET, {"feature_set_id": value}) for value in space.feature_set_ids)
        if InterventionKind.MODEL in allowed:
            values.extend(ResearchIntervention(InterventionKind.MODEL, {"model_spec_id": value}) for value in space.model_spec_ids if value != baseline_id)
        if InterventionKind.PARAMETERS in allowed:
            for name in sorted(space.parameter_choices):
                for value in space.parameter_choices[name]:
                    values.append(ResearchIntervention(InterventionKind.PARAMETERS, {"parameter": name, "value": value}))
        proposals = []
        for index, intervention in enumerate(values, 1):
            proposals.append(CandidateProposal(
                id=f"CANDIDATE-{index:04d}", baseline_model_spec_id=baseline_id, intervention=intervention,
                rationale=(f"Diagnosis {diagnosis} permits {intervention.kind.value} intervention.", *tuple(findings)),
                expected_effect=f"Improve the committed primary metric through {intervention.kind.value}.",
                falsification=("Fails the committed minimum validation improvement.", "Fails the sealed research-OOS improvement gate."),
                priority=index,
            ))
        return tuple(proposals)

    def _fit_candidate(self, proposal: CandidateProposal, baseline: ModelSpec, fit_rows: Sequence[Mapping[str, Any]]):
        kind = proposal.intervention.kind
        values = proposal.intervention.values
        calibration_id = None
        if kind == InterventionKind.MODEL:
            spec = self.runtime.model_specs[str(values["model_spec_id"])]
        elif kind == InterventionKind.FEATURE_SET:
            spec = replace(baseline, id=f"{baseline.id}__{proposal.id}", feature_set=str(values["feature_set_id"]))
        elif kind == InterventionKind.PARAMETERS:
            params = dict(baseline.params); params[str(values["parameter"])] = values["value"]
            spec = replace(baseline, id=f"{baseline.id}__{proposal.id}", params=params)
        elif kind == InterventionKind.CALIBRATION:
            spec = baseline
        else:
            raise ResearchError(f"intervention execution is not yet available for {kind.value}")
        model = self._fit_spec(spec, fit_rows)
        if kind == InterventionKind.CALIBRATION:
            calibrator_id = str(values["calibrator_id"])
            calibrators = {item.id: item for item in self.runtime.plugin.calibrators}
            if calibrator_id not in calibrators:
                raise ResearchError(f"missing capability: calibrator {calibrator_id}")
            materialized, truth = self._materialize_and_target(spec, fit_rows)
            prediction = model.predict(materialized)
            calibration = calibrators[calibrator_id].fit(prediction, truth)
            calibration_id = calibrator_id
            return spec, model, calibration, calibration_id
        return spec, model, None, None

    def _fit_spec(self, spec: ModelSpec, rows: Sequence[Mapping[str, Any]]):
        try:
            trainer = self.runtime.trainer_for(spec.implementation)
        except Exception as exc:
            raise ResearchError(f"missing capability: model trainer {spec.implementation}") from exc
        result = trainer.fit(
            TrainingRequest(
                model_spec=spec, rows=tuple(rows), inputs=self.runtime.prepare_inputs(spec, rows),
                objective=spec.objective, services=self.runtime.plugin.services, partition_id="research_fit",
            )
        )
        predictor = result.predictor
        return predictor.model if isinstance(predictor, LegacyPredictorAdapter) else predictor

    def _materialize_and_target(self, spec: ModelSpec, rows: Sequence[Mapping[str, Any]]):
        if spec.feature_set is None or not spec.objective.target:
            raise ResearchError("calibration currently requires a numeric target and feature-set model")
        feature_set = self.runtime.feature_sets[spec.feature_set]
        materialized = self.runtime.features.materialize(rows, feature_set)
        target = tuple(float(row[spec.objective.target]) for row in rows)
        return materialized, target

    def _primary_metric(self, spec: ModelSpec, model: Any, rows: Sequence[Mapping[str, Any]], *, calibration: Any | None = None) -> float:
        inputs = self.runtime.prepare_inputs(spec, rows)
        request = PredictionRequest(
            model_spec=spec, rows=tuple(rows), inputs=inputs, services=self.runtime.plugin.services, partition_id="research_evaluation",
        )
        try:
            output = model.predict(request)
        except (TypeError, AttributeError):
            output = ModelOutputBatch(tuple(model.predict(inputs.get("features", rows))))
        if not isinstance(output, ModelOutputBatch):
            output = ModelOutputBatch(tuple(output))
        if calibration is not None:
            output = ModelOutputBatch(tuple(calibration.transform(output.values)), output_name=output.output_name)
        context = EvaluationContext(
            model_spec=spec, rows=tuple(rows), outputs=output, objective=spec.objective,
            inputs=inputs, services=self.runtime.plugin.services, partition_id="research_evaluation",
        )
        metrics = self.runtime.evaluate_context(spec, context)
        return float(metrics[spec.evaluation.primary.id])

    def _register_candidate(self, spec: ModelSpec, model: Any, data_source_id: str, proposal: CandidateProposal) -> str:
        trainer = self.runtime.trainer_for(spec.implementation)
        codec = getattr(trainer, "artifact_codec", None)
        if codec is None:
            raise ResearchError(f"missing capability: artifact codec for {spec.implementation}")
        snapshot = self.runtime.data_sources[data_source_id].snapshot()
        from automo.registry import TrainingProvenance
        import platform
        provenance = TrainingProvenance(
            data_source_id=data_source_id, data_snapshot_id=snapshot.id, data_snapshot_hash=snapshot.content_hash,
            feature_set_id=spec.feature_set or "<custom-inputs>", model_spec_id=spec.id, objective_id=spec.objective.id,
            runner_implementation=spec.implementation, python_version=platform.python_version(), seed=None,
            code_revision=self.runtime._git_revision(),
        )
        manifest = self.registry.register_model(
            model, implementation=spec.implementation, model_spec_id=spec.id, objective_id=spec.objective.id,
            feature_set_id=spec.feature_set or "<custom-inputs>", provenance=provenance, codec=codec,
        )
        return manifest.id

    @staticmethod
    def _rows(rows: Sequence[Mapping[str, Any]], indices: Sequence[int]) -> tuple[Mapping[str, Any], ...]:
        return tuple(rows[index] for index in indices)

    @staticmethod
    def _improvement(direction: MetricDirection, baseline: float, candidate: float) -> float:
        return (candidate - baseline) if direction == MetricDirection.MAXIMIZE else (baseline - candidate)
