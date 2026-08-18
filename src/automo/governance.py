"""Research-program governance under ``.automo``.

Automo owns scientific state: model structure, hypotheses, experiments, evidence and
research decisions. Project direction and milestones belong to external project
management (for example GetDone) and are intentionally not represented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any

import yaml


class GovernanceError(RuntimeError):
    pass


STATE_SCHEMA_VERSION = 1


class ModelRole(StrEnum):
    STANDALONE = "standalone"
    SUBMODEL = "submodel"
    META = "meta"
    ENSEMBLE = "ensemble"
    DISTRIBUTION = "distribution"
    DECISION = "decision"


class ModelRelationKind(StrEnum):
    INPUT = "input"
    CORRELATED = "correlated"
    COMPLEMENTARY = "complementary"
    ALTERNATIVE = "alternative"


class ModelCandidateStatus(StrEnum):
    AVAILABLE = "available"
    SELECTED = "selected"
    REJECTED = "rejected"
    RETIRED = "retired"


class HypothesisStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    SUPPORTED = "supported"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class ObjectiveLevel(StrEnum):
    LOCAL = "local"
    PARENT = "parent"
    SYSTEM = "system"


class CompositionExperimentKind(StrEnum):
    INPUT_ABLATION = "input_ablation"
    TARGET_MODEL = "target_model"


class ObjectiveDirection(StrEnum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"
    CONSTRAIN = "constrain"


class EvaluationDepth(IntEnum):
    VALIDITY = 0
    LOCAL = 1
    PARENT = 2
    SYSTEM = 3


@dataclass(frozen=True)
class ResearchProvenance:
    program_id: str
    hypothesis_id: str
    experiment_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "program": self.program_id,
            "hypothesis": self.hypothesis_id,
            "experiment": self.experiment_id,
        }


@dataclass(frozen=True)
class ModelComponent:
    id: str
    role: ModelRole
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "description": self.description,
        }


@dataclass(frozen=True)
class ModelRelation:
    source: str
    target: str
    kind: ModelRelationKind
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind.value,
            "description": self.description,
        }


@dataclass(frozen=True)
class CandidateInput:
    model_id: str
    candidate_id: str

    def as_dict(self) -> dict[str, Any]:
        return {"model": self.model_id, "candidate": self.candidate_id}


@dataclass(frozen=True)
class ModelCandidate:
    id: str
    model_id: str
    model_spec_id: str
    artifact_id: str
    status: ModelCandidateStatus = ModelCandidateStatus.AVAILABLE
    inputs: tuple[CandidateInput, ...] = ()
    provenance: ResearchProvenance | None = None
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": "automo.model_candidate",
            "schema_version": STATE_SCHEMA_VERSION,
            "id": self.id,
            "model": self.model_id,
            "model_spec_id": self.model_spec_id,
            "artifact_id": self.artifact_id,
            "status": self.status.value,
            "inputs": [item.as_dict() for item in self.inputs],
            "provenance": self.provenance.as_dict() if self.provenance else None,
            "description": self.description,
        }


@dataclass(frozen=True)
class CompositionExperiment:
    id: str
    provenance: ResearchProvenance
    target_model: str
    kind: CompositionExperimentKind
    control_candidate_id: str
    treatment_candidate_id: str
    metrics: tuple[str, ...]
    rationale: str
    expected_effect: str
    falsification: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": "automo.composition_experiment",
            "schema_version": STATE_SCHEMA_VERSION,
            "id": self.id,
            "provenance": self.provenance.as_dict(),
            "target_model": self.target_model,
            "kind": self.kind.value,
            "control_candidate": self.control_candidate_id,
            "treatment_candidate": self.treatment_candidate_id,
            "metrics": list(self.metrics),
            "rationale": self.rationale,
            "expected_effect": self.expected_effect,
            "falsification": list(self.falsification),
        }


@dataclass(frozen=True)
class HypothesisObjective:
    metric: str
    level: ObjectiveLevel
    direction: ObjectiveDirection
    required: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "level": self.level.value,
            "direction": self.direction.value,
            "required": self.required,
        }


@dataclass(frozen=True)
class ResearchHypothesis:
    id: str
    statement: str
    status: HypothesisStatus
    parent_id: str | None = None
    primary_model: str | None = None
    related_models: tuple[str, ...] = ()
    objectives: tuple[HypothesisObjective, ...] = ()
    required_evaluation_depth: EvaluationDepth = EvaluationDepth.LOCAL
    conclusion: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": "automo.research_hypothesis",
            "schema_version": STATE_SCHEMA_VERSION,
            "id": self.id,
            "parent": self.parent_id,
            "statement": self.statement,
            "status": self.status.value,
            "scope": {
                "primary_model": self.primary_model,
                "related_models": list(self.related_models),
            },
            "objectives": [item.as_dict() for item in self.objectives],
            "required_evaluation_depth": self.required_evaluation_depth.name.lower(),
            "conclusion": self.conclusion,
        }


class ResearchGovernance:
    """Filesystem authority for Automo's scientific research context."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.state = self.root / ".automo"
        self.research = self.state / "research-program"
        self.hypotheses = self.research / "hypotheses"
        self.candidates = self.research / "candidates"
        self.composition_experiments = self.research / "composition-experiments"

    def initialise(self) -> tuple[Path, ...]:
        project_path = self.state / "project.yaml"
        if project_path.is_file():
            raw = _load_yaml(project_path)
            if raw.get("artifact_type") != "automo.research_project":
                raise GovernanceError(
                    "existing .automo/project.yaml is not an Automo research project"
                )
            if raw.get("schema_version") != STATE_SCHEMA_VERSION:
                raise GovernanceError(
                    f"unsupported research-state schema_version: {raw.get('schema_version')!r}; "
                    "recreate .automo research state using the current Automo version"
                )
        created: list[Path] = []
        for path in (
            self.state,
            self.research,
            self.hypotheses,
            self.candidates,
            self.composition_experiments,
        ):
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                created.append(path.relative_to(self.root))
        defaults = {
            self.state / "project.yaml": {
                "artifact_type": "automo.research_project",
                "schema_version": STATE_SCHEMA_VERSION,
                "program": "default",
                "current_hypothesis": None,
            },
            self.research / "program.yaml": {
                "artifact_type": "automo.research_program",
                "schema_version": STATE_SCHEMA_VERSION,
                "id": "default",
                "title": self.root.name or "Automo research program",
                "root_hypothesis": None,
            },
            self.research / "model-graph.yaml": {
                "artifact_type": "automo.model_graph",
                "schema_version": STATE_SCHEMA_VERSION,
                "models": [],
                "relations": [],
            },
        }
        for path, payload in defaults.items():
            if not path.exists():
                _write_yaml(path, payload)
                created.append(path.relative_to(self.root))
        return tuple(created)

    def register_model(
        self, identifier: str, *, role: ModelRole, description: str = ""
    ) -> ModelComponent:
        self.initialise()
        graph = _load_yaml(self.research / "model-graph.yaml")
        if any(item.get("id") == identifier for item in graph.get("models", [])):
            raise GovernanceError(f"model component already exists: {identifier}")
        model = ModelComponent(identifier, role, description)
        graph.setdefault("models", []).append(model.as_dict())
        _write_yaml(self.research / "model-graph.yaml", graph)
        return model

    def add_model_relation(
        self, source: str, target: str, *, kind: ModelRelationKind, description: str = ""
    ) -> ModelRelation:
        self.initialise()
        if source == target:
            raise GovernanceError("model relation cannot reference the same source and target")
        graph = _load_yaml(self.research / "model-graph.yaml")
        known = {str(item.get("id")) for item in graph.get("models", [])}
        missing = [item for item in (source, target) if item not in known]
        if missing:
            raise GovernanceError(f"unknown model component(s): {', '.join(missing)}")
        if kind == ModelRelationKind.INPUT and self._would_create_input_cycle(
            graph, source, target
        ):
            raise GovernanceError(
                f"input relation would create a model cycle: {source} -> {target}"
            )
        relation = ModelRelation(source, target, kind, description)
        key = (source, target, kind.value)
        if any(
            (item.get("source"), item.get("target"), item.get("kind")) == key
            for item in graph.get("relations", [])
        ):
            raise GovernanceError(
                f"model relation already exists: {source} -> {target} ({kind.value})"
            )
        graph.setdefault("relations", []).append(relation.as_dict())
        _write_yaml(self.research / "model-graph.yaml", graph)
        return relation

    def register_candidate(
        self,
        identifier: str,
        *,
        model_id: str,
        model_spec_id: str,
        artifact_id: str,
        inputs: tuple[CandidateInput, ...] = (),
        provenance: ResearchProvenance | None = None,
        description: str = "",
    ) -> ModelCandidate:
        self.initialise()
        self._require_model(model_id)
        path = self.candidates / f"{identifier}.yaml"
        if path.exists():
            raise GovernanceError(f"model candidate already exists: {identifier}")
        seen_models: set[str] = set()
        for item in inputs:
            if item.model_id in seen_models:
                raise GovernanceError(f"candidate inputs contain duplicate model: {item.model_id}")
            seen_models.add(item.model_id)
            upstream = self.load_candidate(item.candidate_id)
            if upstream.model_id != item.model_id:
                raise GovernanceError(
                    f"candidate {item.candidate_id} belongs to model {upstream.model_id}, not {item.model_id}"
                )
            if not self._has_input_relation(item.model_id, model_id):
                raise GovernanceError(
                    f"model {item.model_id} is not registered as an input to {model_id}"
                )
        candidate = ModelCandidate(
            id=identifier,
            model_id=model_id,
            model_spec_id=model_spec_id,
            artifact_id=artifact_id,
            inputs=inputs,
            provenance=provenance,
            description=description,
        )
        _write_yaml(path, candidate.as_dict())
        return candidate

    def load_candidate(self, identifier: str) -> ModelCandidate:
        path = self.candidates / f"{identifier}.yaml"
        if not path.is_file():
            raise GovernanceError(f"unknown model candidate: {identifier}")
        raw = _load_yaml(path)
        try:
            provenance_raw = raw.get("provenance")
            provenance = None
            if provenance_raw:
                provenance = ResearchProvenance(
                    program_id=str(provenance_raw["program"]),
                    hypothesis_id=str(provenance_raw["hypothesis"]),
                    experiment_id=provenance_raw.get("experiment"),
                )
            return ModelCandidate(
                id=str(raw["id"]),
                model_id=str(raw["model"]),
                model_spec_id=str(raw["model_spec_id"]),
                artifact_id=str(raw["artifact_id"]),
                status=ModelCandidateStatus(str(raw.get("status", "available"))),
                inputs=tuple(
                    CandidateInput(str(item["model"]), str(item["candidate"]))
                    for item in raw.get("inputs", [])
                ),
                provenance=provenance,
                description=str(raw.get("description", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GovernanceError(f"invalid model candidate contract: {path}") from exc

    def select_candidate(self, identifier: str) -> ModelCandidate:
        selected = self.load_candidate(identifier)
        if selected.status in {ModelCandidateStatus.REJECTED, ModelCandidateStatus.RETIRED}:
            raise GovernanceError(
                f"candidate {identifier} cannot be selected while {selected.status.value}"
            )
        for path in sorted(self.candidates.glob("*.yaml")):
            item = self.load_candidate(path.stem)
            if item.model_id != selected.model_id:
                continue
            status = (
                ModelCandidateStatus.SELECTED
                if item.id == identifier
                else (
                    ModelCandidateStatus.AVAILABLE
                    if item.status == ModelCandidateStatus.SELECTED
                    else item.status
                )
            )
            if status != item.status:
                _write_yaml(path, ModelCandidate(**{**item.__dict__, "status": status}).as_dict())
        return self.load_candidate(identifier)

    def selected_candidate(self, model_id: str) -> ModelCandidate | None:
        self._require_model(model_id)
        selected = []
        for path in sorted(self.candidates.glob("*.yaml")):
            candidate = self.load_candidate(path.stem)
            if candidate.model_id == model_id and candidate.status == ModelCandidateStatus.SELECTED:
                selected.append(candidate)
        if len(selected) > 1:
            raise GovernanceError(f"model {model_id} has multiple selected candidates")
        return selected[0] if selected else None

    def create_composition_experiment(
        self,
        identifier: str,
        *,
        hypothesis_id: str,
        target_model: str,
        control_candidate_id: str,
        treatment_candidate_id: str,
        metrics: tuple[str, ...],
        rationale: str,
        expected_effect: str,
        falsification: tuple[str, ...],
    ) -> CompositionExperiment:
        self.initialise()
        hypothesis = self.load_hypothesis(hypothesis_id)
        self._require_model(target_model)
        if hypothesis.primary_model and target_model not in {
            hypothesis.primary_model,
            *hypothesis.related_models,
        }:
            raise GovernanceError(
                f"target model {target_model} is outside hypothesis {hypothesis_id} scope"
            )
        if not metrics:
            raise GovernanceError("composition experiment requires at least one committed metric")
        if not rationale.strip() or not expected_effect.strip() or not falsification:
            raise GovernanceError(
                "composition experiment requires rationale, expected effect, and falsification"
            )
        control = self.load_candidate(control_candidate_id)
        treatment = self.load_candidate(treatment_candidate_id)
        for candidate in (control, treatment):
            if candidate.model_id != target_model:
                raise GovernanceError(
                    f"composition candidate {candidate.id} belongs to {candidate.model_id}, not {target_model}"
                )
        if control.id == treatment.id:
            raise GovernanceError(
                "composition experiment requires distinct immutable control and treatment candidates"
            )
        control_inputs = {(item.model_id, item.candidate_id) for item in control.inputs}
        treatment_inputs = {(item.model_id, item.candidate_id) for item in treatment.inputs}
        spec_changed = control.model_spec_id != treatment.model_spec_id
        inputs_changed = control_inputs != treatment_inputs
        if spec_changed and inputs_changed:
            raise GovernanceError(
                "composition experiment is confounded: target model spec and upstream inputs both changed"
            )
        if not spec_changed and not inputs_changed:
            raise GovernanceError(
                "composition experiment changes neither target model spec nor upstream candidate composition"
            )
        kind = (
            CompositionExperimentKind.TARGET_MODEL
            if spec_changed
            else CompositionExperimentKind.INPUT_ABLATION
        )
        path = self.composition_experiments / f"{identifier}.yaml"
        if path.exists():
            raise GovernanceError(f"composition experiment already exists: {identifier}")
        project = _load_yaml(self.state / "project.yaml")
        provenance = ResearchProvenance(
            program_id=str(project.get("program", "default")),
            hypothesis_id=hypothesis_id,
            experiment_id=identifier,
        )
        experiment = CompositionExperiment(
            identifier,
            provenance,
            target_model,
            kind,
            control.id,
            treatment.id,
            metrics,
            rationale,
            expected_effect,
            falsification,
        )
        _write_yaml(path, experiment.as_dict())
        return experiment

    @staticmethod
    def _would_create_input_cycle(graph: dict[str, Any], source: str, target: str) -> bool:
        adjacency: dict[str, set[str]] = {}
        for item in graph.get("relations", []):
            if item.get("kind") == ModelRelationKind.INPUT.value:
                adjacency.setdefault(str(item.get("source")), set()).add(str(item.get("target")))
        adjacency.setdefault(source, set()).add(target)
        stack = [target]
        seen: set[str] = set()
        while stack:
            node = stack.pop()
            if node == source:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(adjacency.get(node, ()))
        return False

    def _require_model(self, identifier: str) -> None:
        graph = _load_yaml(self.research / "model-graph.yaml")
        if identifier not in {str(item.get("id")) for item in graph.get("models", [])}:
            raise GovernanceError(f"unknown model component: {identifier}")

    def _has_input_relation(self, source: str, target: str) -> bool:
        graph = _load_yaml(self.research / "model-graph.yaml")
        return any(
            item.get("source") == source
            and item.get("target") == target
            and item.get("kind") == ModelRelationKind.INPUT.value
            for item in graph.get("relations", [])
        )

    def create_hypothesis(
        self,
        identifier: str,
        *,
        statement: str,
        parent_id: str | None = None,
        primary_model: str | None = None,
        related_models: tuple[str, ...] = (),
        objectives: tuple[HypothesisObjective, ...] = (),
        required_evaluation_depth: EvaluationDepth = EvaluationDepth.LOCAL,
    ) -> ResearchHypothesis:
        self.initialise()
        path = self.hypotheses / f"{identifier}.yaml"
        if path.exists():
            raise GovernanceError(f"research hypothesis already exists: {identifier}")
        if parent_id is not None:
            self.load_hypothesis(parent_id)
        graph = _load_yaml(self.research / "model-graph.yaml")
        known_models = {str(item.get("id")) for item in graph.get("models", [])}
        referenced = tuple(item for item in (primary_model, *related_models) if item)
        unknown = sorted(set(referenced) - known_models)
        if unknown:
            raise GovernanceError(f"unknown model component(s): {', '.join(unknown)}")
        hypothesis = ResearchHypothesis(
            id=identifier,
            statement=statement,
            status=HypothesisStatus.PROPOSED,
            parent_id=parent_id,
            primary_model=primary_model,
            related_models=related_models,
            objectives=objectives,
            required_evaluation_depth=required_evaluation_depth,
        )
        _write_yaml(path, hypothesis.as_dict())
        program = _load_yaml(self.research / "program.yaml")
        if program.get("root_hypothesis") is None and parent_id is None:
            program["root_hypothesis"] = identifier
            _write_yaml(self.research / "program.yaml", program)
        return hypothesis

    def load_hypothesis(self, identifier: str) -> ResearchHypothesis:
        path = self.hypotheses / f"{identifier}.yaml"
        if not path.is_file():
            raise GovernanceError(f"unknown research hypothesis: {identifier}")
        raw = _load_yaml(path)
        try:
            scope = raw.get("scope") or {}
            objectives = tuple(
                HypothesisObjective(
                    metric=str(item["metric"]),
                    level=ObjectiveLevel(str(item["level"])),
                    direction=ObjectiveDirection(str(item["direction"])),
                    required=bool(item.get("required", True)),
                )
                for item in raw.get("objectives", [])
            )
            depth = EvaluationDepth[str(raw.get("required_evaluation_depth", "local")).upper()]
            return ResearchHypothesis(
                id=str(raw["id"]),
                statement=str(raw["statement"]),
                status=HypothesisStatus(str(raw["status"])),
                parent_id=raw.get("parent"),
                primary_model=scope.get("primary_model"),
                related_models=tuple(scope.get("related_models", [])),
                objectives=objectives,
                required_evaluation_depth=depth,
                conclusion=raw.get("conclusion"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise GovernanceError(f"invalid research hypothesis contract: {path}") from exc

    def activate_hypothesis(self, identifier: str) -> ResearchHypothesis:
        hypothesis = self.load_hypothesis(identifier)
        if hypothesis.status not in {HypothesisStatus.PROPOSED, HypothesisStatus.ACTIVE}:
            raise GovernanceError(
                f"concluded research hypothesis cannot be activated: {identifier}"
            )
        updated = ResearchHypothesis(**{**hypothesis.__dict__, "status": HypothesisStatus.ACTIVE})
        _write_yaml(self.hypotheses / f"{identifier}.yaml", updated.as_dict())
        project = _load_yaml(self.state / "project.yaml")
        project["current_hypothesis"] = identifier
        _write_yaml(self.state / "project.yaml", project)
        return updated

    def conclude_hypothesis(
        self, identifier: str, *, status: HypothesisStatus, conclusion: str
    ) -> ResearchHypothesis:
        if status not in {
            HypothesisStatus.SUPPORTED,
            HypothesisStatus.REJECTED,
            HypothesisStatus.INCONCLUSIVE,
        }:
            raise GovernanceError(
                "hypothesis conclusion status must be supported, rejected, or inconclusive"
            )
        hypothesis = self.load_hypothesis(identifier)
        if hypothesis.status != HypothesisStatus.ACTIVE:
            raise GovernanceError("only an active research hypothesis can be concluded")
        updated = ResearchHypothesis(
            **{**hypothesis.__dict__, "status": status, "conclusion": conclusion}
        )
        _write_yaml(self.hypotheses / f"{identifier}.yaml", updated.as_dict())
        project = _load_yaml(self.state / "project.yaml")
        if project.get("current_hypothesis") == identifier:
            project["current_hypothesis"] = None
            _write_yaml(self.state / "project.yaml", project)
        return updated

    def current_hypothesis(self) -> ResearchHypothesis | None:
        if not (self.state / "project.yaml").is_file():
            return None
        project = _load_yaml(self.state / "project.yaml")
        identifier = project.get("current_hypothesis")
        return self.load_hypothesis(str(identifier)) if identifier else None

    def require_execution_ready(self) -> ResearchHypothesis | None:
        if not (self.state / "project.yaml").is_file():
            return None
        hypothesis = self.current_hypothesis()
        if hypothesis is None:
            raise GovernanceError(
                "no active research hypothesis; activate the hypothesis this experiment is testing"
            )
        if hypothesis.status != HypothesisStatus.ACTIVE:
            raise GovernanceError(
                f"research hypothesis {hypothesis.id} is {hypothesis.status.value}; activate it before executing research"
            )
        return hypothesis

    def provenance(self, experiment_id: str | None = None) -> ResearchProvenance:
        hypothesis = self.require_execution_ready()
        if hypothesis is None:
            raise GovernanceError("research provenance requires an initialized research program")
        project = _load_yaml(self.state / "project.yaml")
        return ResearchProvenance(
            str(project.get("program", "default")), hypothesis.id, experiment_id
        )

    def status_payload(self) -> dict[str, Any]:
        self.initialise()
        program = _load_yaml(self.research / "program.yaml")
        graph = _load_yaml(self.research / "model-graph.yaml")
        hypothesis = self.current_hypothesis()
        return {
            "program": {"id": program.get("id"), "root_hypothesis": program.get("root_hypothesis")},
            "current_hypothesis": hypothesis.as_dict() if hypothesis else None,
            "models": graph.get("models", []),
            "relations": graph.get("relations", []),
        }

    def hypothesis_tree(self) -> tuple[tuple[int, ResearchHypothesis], ...]:
        self.initialise()
        hypotheses = [
            self.load_hypothesis(path.stem) for path in sorted(self.hypotheses.glob("*.yaml"))
        ]
        by_parent: dict[str | None, list[ResearchHypothesis]] = {}
        for item in hypotheses:
            by_parent.setdefault(item.parent_id, []).append(item)
        rows: list[tuple[int, ResearchHypothesis]] = []
        seen: set[str] = set()

        def visit(item: ResearchHypothesis, depth: int) -> None:
            if item.id in seen:
                raise GovernanceError(f"cycle detected in hypothesis graph at {item.id}")
            seen.add(item.id)
            rows.append((depth, item))
            for child in sorted(by_parent.get(item.id, []), key=lambda value: value.id):
                visit(child, depth + 1)

        for root in sorted(by_parent.get(None, []), key=lambda value: value.id):
            visit(root, 0)
        if len(seen) != len(hypotheses):
            raise GovernanceError("hypothesis graph contains unreachable or cyclic nodes")
        return tuple(rows)

    def validate(self) -> tuple[str, ...]:
        if not self.state.exists():
            return ()
        errors: list[str] = []
        required = (
            (self.state / "project.yaml", "automo.research_project"),
            (self.research / "program.yaml", "automo.research_program"),
            (self.research / "model-graph.yaml", "automo.model_graph"),
        )
        for path, artifact_type in required:
            if not path.is_file():
                errors.append(
                    f"missing Automo research-state contract: {path.relative_to(self.root)}"
                )
                continue
            raw = _load_yaml(path)
            if raw.get("artifact_type") != artifact_type:
                errors.append(f"{path.relative_to(self.root)} has wrong artifact_type")
            if raw.get("schema_version") != STATE_SCHEMA_VERSION:
                errors.append(
                    f"{path.relative_to(self.root)} schema_version must be {STATE_SCHEMA_VERSION}"
                )
        if errors:
            return tuple(errors)
        try:
            self.hypothesis_tree()
            graph = _load_yaml(self.research / "model-graph.yaml")
            models = [str(item.get("id")) for item in graph.get("models", [])]
            if len(models) != len(set(models)):
                errors.append("model graph contains duplicate model ids")
            known = set(models)
            for relation in graph.get("relations", []):
                if relation.get("source") not in known or relation.get("target") not in known:
                    errors.append("model graph relation references an unknown model")
        except GovernanceError as exc:
            errors.append(str(exc))
        return tuple(errors)


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise GovernanceError(f"cannot read research-state contract: {path}") from exc
    if not isinstance(value, dict):
        raise GovernanceError(f"research-state contract must be a mapping: {path}")
    return value


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
