from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from automo.persistence import read_json_artifact, write_json_artifact

from .contracts import CandidateProposal, ResearchIterationReport, ResearchPlan


class ResearchStoreError(RuntimeError):
    pass


class FilesystemResearchStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def iteration_dir(self, iteration_id: str) -> Path:
        return self.root / iteration_id

    def create_plan(self, plan: ResearchPlan) -> Path:
        directory = self.iteration_dir(plan.id)
        if directory.exists():
            raise ResearchStoreError(f"research iteration already exists: {plan.id}")
        directory.mkdir(parents=True)
        payload = {
            "id": plan.id,
            "provenance": plan.provenance.as_dict() if plan.provenance else None,
            "baseline_model_spec_id": plan.baseline_model_spec_id,
            "data_source_id": plan.data_source_id,
            "split_strategy_id": plan.split_strategy_id,
            "diagnosis": plan.diagnosis,
            "findings": list(plan.findings),
            "search_space": asdict(plan.search_space),
            "budget": asdict(plan.budget),
            "safeguards": asdict(plan.safeguards),
            "candidates": [self._proposal_dict(item) for item in plan.candidates],
        }
        path = directory / "plan.json"
        write_json_artifact(path, artifact_type="automo.research_plan", payload=payload)
        return path

    def write_report(self, report: ResearchIterationReport) -> Path:
        directory = self.iteration_dir(report.id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "report.json"
        if path.exists():
            raise ResearchStoreError(f"research report already exists: {report.id}")
        write_json_artifact(path, artifact_type="automo.research_report", payload=report.as_dict())
        return path

    def fingerprints(self) -> set[str]:
        values: set[str] = set()
        for path in self.root.glob("*/plan.json"):
            try:
                raw = read_json_artifact(path, artifact_type="automo.research_plan")
            except Exception:
                continue
            for item in raw.get("candidates", []):
                if isinstance(item, dict) and item.get("fingerprint"):
                    values.add(str(item["fingerprint"]))
        return values

    def history(self) -> Iterable[Path]:
        return sorted(self.root.glob("*/report.json"))

    @staticmethod
    def _proposal_dict(item: CandidateProposal) -> dict:
        return {
            "id": item.id,
            "baseline_model_spec_id": item.baseline_model_spec_id,
            "intervention": item.intervention.fingerprint_payload(),
            "rationale": list(item.rationale),
            "expected_effect": item.expected_effect,
            "falsification": list(item.falsification),
            "priority": item.priority,
            "fingerprint": item.fingerprint,
        }

    def load_plan(self, iteration_id: str):
        from .contracts import (
            CandidateProposal,
            InterventionKind,
            ResearchBudget,
            ResearchIntervention,
            ResearchPlan,
            ResearchSafeguards,
            ResearchSearchSpace,
        )

        path = self.iteration_dir(iteration_id) / "plan.json"
        if not path.is_file():
            raise ResearchStoreError(f"unknown research iteration: {iteration_id}")
        raw = read_json_artifact(path, artifact_type="automo.research_plan")
        space_raw = raw["search_space"]
        space = ResearchSearchSpace(
            id=space_raw["id"],
            model_spec_ids=tuple(space_raw.get("model_spec_ids", [])),
            feature_set_ids=tuple(space_raw.get("feature_set_ids", [])),
            calibrator_ids=tuple(space_raw.get("calibrator_ids", [])),
            parameter_choices={
                k: tuple(v) for k, v in space_raw.get("parameter_choices", {}).items()
            },
            maximum_compound_interventions=int(space_raw.get("maximum_compound_interventions", 1)),
        )
        budget = ResearchBudget(**raw["budget"])
        safeguards = ResearchSafeguards(**raw["safeguards"])
        candidates = []
        for item in raw["candidates"]:
            iv = item["intervention"]
            candidates.append(
                CandidateProposal(
                    id=item["id"],
                    baseline_model_spec_id=item["baseline_model_spec_id"],
                    intervention=ResearchIntervention(InterventionKind(iv["kind"]), iv["values"]),
                    rationale=tuple(item.get("rationale", [])),
                    expected_effect=item.get("expected_effect", ""),
                    falsification=tuple(item.get("falsification", [])),
                    priority=int(item.get("priority", 0)),
                )
            )
        from automo.governance import ResearchProvenance

        provenance_raw = raw.get("provenance")
        provenance = None
        if provenance_raw:
            provenance = ResearchProvenance(
                program_id=provenance_raw["program"],
                hypothesis_id=provenance_raw["hypothesis"],
                experiment_id=provenance_raw.get("experiment"),
            )
        return ResearchPlan(
            id=raw["id"],
            provenance=provenance,
            baseline_model_spec_id=raw["baseline_model_spec_id"],
            data_source_id=raw["data_source_id"],
            split_strategy_id=raw["split_strategy_id"],
            diagnosis=raw["diagnosis"],
            findings=tuple(raw.get("findings", [])),
            search_space=space,
            budget=budget,
            safeguards=safeguards,
            candidates=tuple(candidates),
        )
